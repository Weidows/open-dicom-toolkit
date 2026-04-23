"""DICOM De-identification (DeID) Operator.

Implements DICOM PS3.15 Appendix E compliant de-identification
with three modes: remove, pseudonymize, and date_shift.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import pydicom
    from pydicom.dataset import Dataset
    from pydicom.uid import generate_uid
except ImportError:
    pydicom = None
    Dataset = None
    generate_uid = None

from src.core import OperatorBase, OperatorMeta

logger = logging.getLogger(__name__)

# Tags to de-identify per DICOM PS3.15 Appendix E
# Format: (group, element) -> action
DEID_TAGS = {
    # Patient Identity
    (0x0010, 0x0010): "PatientName",
    (0x0010, 0x0020): "PatientID",
    (0x0010, 0x0030): "PatientBirthDate",
    (0x0010, 0x0032): "PatientBirthTime",
    (0x0010, 0x0040): "PatientSex",
    (0x0010, 0x1000): "OtherPatientIDs",
    (0x0010, 0x1001): "OtherPatientNames",
    (0x0010, 0x1090): "MedicalRecordLocator",
    (0x0010, 0x2160): "EthnicGroup",
    (0x0010, 0x2180): "Occupation",
    (0x0010, 0x21B0): "AdditionalPatientHistory",
    (0x0010, 0x4000): "PatientComments",
    # Institution
    (0x0008, 0x0080): "InstitutionName",
    (0x0008, 0x0081): "InstitutionAddress",
    (0x0008, 0x1040): "InstitutionalDepartmentName",
    # Physicians
    (0x0008, 0x0090): "ReferringPhysicianName",
    (0x0008, 0x0096): "ReferringPhysicianIdentificationSequence",
    (0x0008, 0x1048): "PhysiciansOfRecord",
    (0x0008, 0x1049): "PhysiciansOfRecordIdentificationSequence",
    (0x0008, 0x1050): "PerformingPhysicianName",
    (0x0008, 0x1052): "PerformingPhysicianIdentificationSequence",
    (0x0008, 0x1060): "NameOfPhysiciansReadingStudy",
    (0x0008, 0x1062): "PhysiciansReadingStudyIdentificationSequence",
    (0x0008, 0x1070): "OperatorsName",
    (0x0008, 0x1072): "OperatorIdentificationSequence",
    # Device / Station
    (0x0008, 0x1010): "StationName",
    (0x0018, 0x1000): "DeviceSerialNumber",
    (0x0018, 0x1002): "DeviceUID",
    (0x0018, 0x1030): "ProtocolName",
    # Dates
    (0x0008, 0x0012): "InstanceCreationDate",
    (0x0008, 0x0013): "InstanceCreationTime",
    (0x0008, 0x0020): "StudyDate",
    (0x0008, 0x0021): "SeriesDate",
    (0x0008, 0x0022): "AcquisitionDate",
    (0x0008, 0x0023): "ContentDate",
    (0x0008, 0x002A): "AcquisitionDateTime",
    (0x0008, 0x0030): "StudyTime",
    (0x0008, 0x0031): "SeriesTime",
    (0x0008, 0x0032): "AcquisitionTime",
    (0x0008, 0x0033): "ContentTime",
    # Study / Series IDs
    (0x0008, 0x0050): "AccessionNumber",
    (0x0020, 0x0010): "StudyID",
    # UIDs
    (0x0008, 0x0014): "InstanceCreatorUID",
    (0x0008, 0x0016): "SOPClassUID",  # Keep - required for file type
    (0x0008, 0x0018): "SOPInstanceUID",
    (0x0020, 0x000D): "StudyInstanceUID",
    (0x0020, 0x000E): "SeriesInstanceUID",
    (0x0020, 0x0052): "FrameOfReferenceUID",
    # Other
    (0x0008, 0x103E): "SeriesDescription",
    (0x0008, 0x1030): "StudyDescription",
    (0x0010, 0x21C0): "PregnancyStatus",
    (0x0010, 0x4000): "PatientComments",
    (0x0040, 0x0244): "PerformedProcedureStepStartDate",
    (0x0040, 0x0245): "PerformedProcedureStepStartTime",
    (0x0040, 0x0253): "PerformedProcedureStepID",
    (0x0040, 0x0254): "PerformedProcedureStepDescription",
}

# Tags that must be regenerated (UIDs)
UID_TAGS = [
    (0x0008, 0x0014),
    (0x0008, 0x0018),
    (0x0020, 0x000D),
    (0x0020, 0x000E),
    (0x0020, 0x0052),
]

# Tags that are dates
DATE_TAGS = [
    (0x0008, 0x0012),
    (0x0008, 0x0020),
    (0x0008, 0x0021),
    (0x0008, 0x0022),
    (0x0008, 0x0023),
    (0x0010, 0x0030),
    (0x0040, 0x0244),
]

# Tags that are times
TIME_TAGS = [
    (0x0008, 0x0013),
    (0x0008, 0x0030),
    (0x0008, 0x0031),
    (0x0008, 0x0032),
    (0x0008, 0x0033),
    (0x0010, 0x0032),
    (0x0040, 0x0245),
]

# Tags that can be kept (whitelist for research)
RESEARCH_KEEP_TAGS = [
    (0x0010, 0x0040),  # PatientSex
    (0x0010, 0x1010),  # PatientAge
    (0x0010, 0x1020),  # PatientSize
    (0x0010, 0x1030),  # PatientWeight
]


class DICOMDeidentifier(OperatorBase):
    """De-identify DICOM files according to PS3.15 Appendix E.

    Supports three modes:
    - remove: Clear sensitive tags
    - pseudonymize: Replace with deterministic hash
    - date_shift: Offset dates by random amount (preserves intervals)

    Example:
        op = DICOMDeidentifier({
            "mode": "pseudonymize",
            "output_dir": "output/deid",
            "salt": "my_secret_salt",
            "keep_tags": ["PatientSex", "PatientAge"],
            "audit_log": True,
        })
        result = op.run({"path": "data/exam.dcm"})
    """

    name = "dicom_deidentifier"
    version = "0.1.0"
    capabilities = ["deidentify", "anonymize", "privacy", "DICOM"]
    input_schema = {"path": "str"}
    output_schema = {"deid_path": "str", "audit_log": "dict"}

    def __init__(self, config: dict):
        super().__init__(config)
        self.mode = config.get("mode", "remove")
        self.output_dir = config.get("output_dir", "output/deid")
        self.salt = config.get("salt", "")
        self.date_shift_days = config.get("date_shift_days", 0)
        self.keep_tags = set(config.get("keep_tags", []))
        self.enable_audit = config.get("audit_log", True)
        self.regenerate_uids = config.get("regenerate_uids", True)

        # Validate mode
        if self.mode not in ("remove", "pseudonymize", "date_shift"):
            raise ValueError(f"Invalid mode: {self.mode}. Must be remove, pseudonymize, or date_shift")

        # Generate random date shift if not provided
        if self.mode == "date_shift" and self.date_shift_days == 0:
            import random
            self.date_shift_days = random.randint(-3650, 3650)

        # UID mapping for consistency within a session
        self._uid_map: dict[str, str] = {}

    def run(self, ctx: dict) -> dict:
        """De-identify DICOM file(s).

        Args:
            ctx: Must contain 'path' key. Optional 'output_dir' override.

        Returns:
            ctx with 'deid_path' and 'audit_log' keys.
        """
        if pydicom is None:
            ctx["error"] = "pydicom not installed"
            return ctx

        path = ctx.get("path")
        if not path:
            ctx["error"] = "No path provided"
            return ctx

        output_dir = ctx.get("output_dir", self.output_dir)

        try:
            if os.path.isdir(path):
                result = self._deidentify_directory(path, output_dir)
            else:
                result = self._deidentify_file(path, output_dir)

            ctx["deid_path"] = result["output_path"]
            if self.enable_audit:
                ctx["audit_log"] = result["audit"]

        except Exception as e:
            ctx["error"] = f"De-identification failed: {e}"
            logger.exception("De-identification failed for %s", path)

        return ctx

    def _deidentify_file(self, file_path: str, output_dir: str) -> dict:
        """De-identify a single DICOM file.

        Returns:
            dict with 'output_path' and 'audit' keys.
        """
        ds = pydicom.dcmread(file_path)
        audit = {
            "source": file_path,
            "mode": self.mode,
            "modifications": [],
        }

        # Process each de-id tag
        for tag, keyword in DEID_TAGS.items():
            # Skip if in keep list
            if keyword in self.keep_tags:
                continue

            # Skip SOPClassUID - required for file type identification
            if tag == (0x0008, 0x0016):
                continue

            if tag in ds:
                original_value = str(ds[tag].value) if ds[tag].value is not None else ""
                new_value = self._transform_value(tag, keyword, original_value, ds)

                if new_value != original_value:
                    audit["modifications"].append({
                        "tag": f"({tag[0]:04X},{tag[1]:04X})",
                        "keyword": keyword,
                        "original": original_value[:100] if len(original_value) < 100 else original_value[:100] + "...",
                        "new": str(new_value)[:100],
                    })
                    ds[tag].value = new_value

        # Handle sequences that may contain PHI
        self._deidentify_sequences(ds, audit)

        # Save
        os.makedirs(output_dir, exist_ok=True)
        output_name = self._generate_output_name(file_path, ds)
        output_path = os.path.join(output_dir, output_name)
        ds.save_as(output_path, write_like_original=False)

        audit["output"] = output_path
        audit["uid_mapping"] = dict(self._uid_map)

        return {"output_path": output_path, "audit": audit}

    def _deidentify_directory(self, dir_path: str, output_dir: str) -> dict:
        """De-identify all DICOM files in a directory."""
        dcm_files = list(Path(dir_path).rglob("*"))
        # Filter for DICOM files (check magic number or extension)
        dcm_files = [f for f in dcm_files if f.is_file()]

        results = []
        all_audits = []

        for file_path in dcm_files:
            try:
                # Quick check if it's a DICOM file
                with open(file_path, "rb") as f:
                    header = f.read(132)
                    if len(header) < 132 or header[128:132] != b"DICM":
                        # Might be implicit VR, try reading
                        try:
                            pydicom.dcmread(str(file_path), stop_before_pixels=True)
                        except Exception:
                            continue

                rel_path = file_path.relative_to(dir_path)
                file_output_dir = os.path.join(output_dir, str(rel_path.parent))
                result = self._deidentify_file(str(file_path), file_output_dir)
                results.append(result["output_path"])
                all_audits.append(result["audit"])

            except Exception as e:
                logger.warning("Skipping %s: %s", file_path, e)

        # Aggregate audit
        aggregate_audit = {
            "source": dir_path,
            "mode": self.mode,
            "files_processed": len(results),
            "file_audits": all_audits,
            "uid_mapping": dict(self._uid_map),
        }

        return {"output_path": output_dir, "audit": aggregate_audit}

    def _transform_value(self, tag: tuple, keyword: str, original: str, ds: Dataset) -> str:
        """Transform a single tag value based on mode."""
        if self.mode == "remove":
            if tag in UID_TAGS:
                return generate_uid() if generate_uid else ""
            return ""

        elif self.mode == "pseudonymize":
            if tag in UID_TAGS and self.regenerate_uids:
                return self._get_mapped_uid(original)
            if tag in DATE_TAGS:
                # Use fixed date for dates in pseudonymize mode
                return "19000101"
            if tag in TIME_TAGS:
                return "000000"
            return self._pseudonymize(original, keyword)

        elif self.mode == "date_shift":
            if tag in UID_TAGS and self.regenerate_uids:
                return self._get_mapped_uid(original)
            if tag in DATE_TAGS:
                return self._shift_date(original)
            if tag in TIME_TAGS:
                return self._shift_time(original)
            return self._pseudonymize(original, keyword)

        return original

    def _pseudonymize(self, value: str, context: str) -> str:
        """Generate a deterministic pseudonym."""
        if not value:
            return ""
        hash_input = f"{self.salt}:{context}:{value}".encode("utf-8")
        hash_bytes = hashlib.sha256(hash_input).hexdigest()[:16]
        return f"ANON_{hash_bytes.upper()}"

    def _get_mapped_uid(self, original_uid: str) -> str:
        """Get or generate a consistent mapped UID."""
        if not original_uid:
            return generate_uid() if generate_uid else ""
        if original_uid not in self._uid_map:
            self._uid_map[original_uid] = generate_uid() if generate_uid else ""
        return self._uid_map[original_uid]

    def _shift_date(self, date_str: str) -> str:
        """Shift a DICOM date string by configured days."""
        if not date_str or len(date_str) < 8:
            return date_str
        try:
            dt = datetime.strptime(date_str[:8], "%Y%m%d")
            shifted = dt + timedelta(days=self.date_shift_days)
            return shifted.strftime("%Y%m%d")
        except ValueError:
            return date_str

    def _shift_time(self, time_str: str) -> str:
        """Shift a DICOM time string by configured days."""
        if not time_str:
            return time_str
        try:
            # DICOM time format: HHMMSS.FFFFFF
            time_part = time_str[:6]
            frac_part = time_str[6:] if len(time_str) > 6 else ""
            dt = datetime.strptime(time_part, "%H%M%S")
            shifted = dt + timedelta(days=self.date_shift_days)
            return shifted.strftime("%H%M%S") + frac_part
        except ValueError:
            return time_str

    def _deidentify_sequences(self, ds: Dataset, audit: dict):
        """Recursively de-identify sequences that may contain PHI."""
        for elem in ds:
            if elem.VR == "SQ":
                for item in elem.value:
                    for sub_tag, sub_keyword in DEID_TAGS.items():
                        if sub_keyword in self.keep_tags:
                            continue
                        if sub_tag in item:
                            original = str(item[sub_tag].value) if item[sub_tag].value is not None else ""
                            new_value = self._transform_value(sub_tag, sub_keyword, original, item)
                            if new_value != original:
                                audit["modifications"].append({
                                    "tag": f"({sub_tag[0]:04X},{sub_tag[1]:04X})",
                                    "keyword": sub_keyword,
                                    "in_sequence": elem.keyword or "Unknown",
                                    "original": original[:100],
                                    "new": str(new_value)[:100],
                                })
                                item[sub_tag].value = new_value

    def _generate_output_name(self, original_path: str, ds: Dataset) -> str:
        """Generate output filename based on SOPInstanceUID."""
        sop_uid = ds.get("SOPInstanceUID", "")
        if sop_uid:
            return f"{sop_uid.replace('.', '_')}.dcm"
        return os.path.basename(original_path)


class DeidAuditLogger:
    """Audit logger for de-identification operations."""

    def __init__(self, log_dir: str = "output/audit"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def save(self, audit: dict, filename: Optional[str] = None) -> str:
        """Save audit log to JSON file.

        Args:
            audit: Audit dictionary from DICOMDeidentifier
            filename: Optional filename, defaults to timestamp-based

        Returns:
            Path to saved audit file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"deid_audit_{timestamp}.json"

        filepath = os.path.join(self.log_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(audit, f, indent=2, ensure_ascii=False, default=str)

        return filepath
