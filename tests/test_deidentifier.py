"""Tests for DICOM de-identification operator."""

import os
import tempfile
from pathlib import Path

import pydicom
import pytest
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from src.operators.deidentifier import DICOMDeidentifier, DeidAuditLogger


@pytest.fixture
def sample_dicom():
    """Create a sample DICOM file with PHI."""
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Patient info
    ds.PatientName = "Test^Patient^Name"
    ds.PatientID = "PATIENT_12345"
    ds.PatientBirthDate = "19900115"
    ds.PatientSex = "M"

    # Study info
    ds.StudyDate = "20240115"
    ds.StudyTime = "103000"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.StudyID = "1"
    ds.AccessionNumber = "ACC123456"

    # Institution
    ds.InstitutionName = "Test Hospital"
    ds.InstitutionAddress = "123 Medical St"

    # Physician
    ds.ReferringPhysicianName = "Dr^Smith"
    ds.PerformingPhysicianName = "Dr^Jones"

    # Device
    ds.StationName = "CT_SCANNER_01"
    ds.ProtocolName = "Chest CT"

    # Image data
    ds.Rows = 64
    ds.Columns = 64
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.SamplesPerPixel = 1
    ds.PixelRepresentation = 0
    ds.Modality = "CT"
    ds.PixelData = b"\x00" * (64 * 64 * 2)

    return ds


@pytest.fixture
def temp_dicom_file(sample_dicom):
    """Save sample DICOM to temp file."""
    with tempfile.NamedTemporaryFile(suffix=".dcm", delete=False) as f:
        sample_dicom.save_as(f.name)
        yield f.name
    os.unlink(f.name)


class TestDICOMDeidentifierRemove:
    """Test remove mode."""

    def test_remove_patient_info(self, temp_dicom_file):
        op = DICOMDeidentifier({"mode": "remove", "output_dir": tempfile.mkdtemp()})
        result = op.run({"path": temp_dicom_file})

        assert "error" not in result
        assert os.path.exists(result["deid_path"])

        ds = pydicom.dcmread(result["deid_path"])
        assert ds.PatientName == ""
        assert ds.PatientID == ""
        assert ds.PatientBirthDate == ""

    def test_remove_institution_info(self, temp_dicom_file):
        op = DICOMDeidentifier({"mode": "remove", "output_dir": tempfile.mkdtemp()})
        result = op.run({"path": temp_dicom_file})

        ds = pydicom.dcmread(result["deid_path"])
        assert ds.InstitutionName == ""
        assert ds.InstitutionAddress == ""

    def test_remove_physician_info(self, temp_dicom_file):
        op = DICOMDeidentifier({"mode": "remove", "output_dir": tempfile.mkdtemp()})
        result = op.run({"path": temp_dicom_file})

        ds = pydicom.dcmread(result["deid_path"])
        assert ds.ReferringPhysicianName == ""
        assert ds.PerformingPhysicianName == ""

    def test_keep_sop_class_uid(self, temp_dicom_file):
        """SOPClassUID should be preserved for file type identification."""
        original = pydicom.dcmread(temp_dicom_file)
        original_uid = original.SOPClassUID

        op = DICOMDeidentifier({"mode": "remove", "output_dir": tempfile.mkdtemp()})
        result = op.run({"path": temp_dicom_file})

        ds = pydicom.dcmread(result["deid_path"])
        assert ds.SOPClassUID == original_uid

    def test_regenerate_uids(self, temp_dicom_file):
        original = pydicom.dcmread(temp_dicom_file)
        original_study_uid = original.StudyInstanceUID

        op = DICOMDeidentifier({"mode": "remove", "output_dir": tempfile.mkdtemp(), "regenerate_uids": True})
        result = op.run({"path": temp_dicom_file})

        ds = pydicom.dcmread(result["deid_path"])
        assert ds.StudyInstanceUID != original_study_uid
        assert ds.SeriesInstanceUID != original.SeriesInstanceUID
        assert ds.SOPInstanceUID != original.SOPInstanceUID

    def test_audit_log(self, temp_dicom_file):
        op = DICOMDeidentifier({"mode": "remove", "output_dir": tempfile.mkdtemp(), "audit_log": True})
        result = op.run({"path": temp_dicom_file})

        assert "audit_log" in result
        audit = result["audit_log"]
        assert audit["mode"] == "remove"
        assert audit["source"] == temp_dicom_file
        assert len(audit["modifications"]) > 0

        # Check PatientName was logged
        patient_mods = [m for m in audit["modifications"] if m["keyword"] == "PatientName"]
        assert len(patient_mods) == 1
        assert "Test^Patient^Name" in patient_mods[0]["original"]


class TestDICOMDeidentifierPseudonymize:
    """Test pseudonymize mode."""

    def test_pseudonymize_patient_info(self, temp_dicom_file):
        op = DICOMDeidentifier({
            "mode": "pseudonymize",
            "salt": "test_salt",
            "output_dir": tempfile.mkdtemp(),
        })
        result = op.run({"path": temp_dicom_file})

        ds = pydicom.dcmread(result["deid_path"])
        assert str(ds.PatientName).startswith("ANON_")
        assert str(ds.PatientID).startswith("ANON_")
        assert str(ds.PatientName) != "Test^Patient^Name"

    def test_deterministic_pseudonym(self, temp_dicom_file):
        """Same input with same salt should produce same pseudonym."""
        op1 = DICOMDeidentifier({
            "mode": "pseudonymize",
            "salt": "test_salt",
            "output_dir": tempfile.mkdtemp(),
        })
        result1 = op1.run({"path": temp_dicom_file})
        ds1 = pydicom.dcmread(result1["deid_path"])

        op2 = DICOMDeidentifier({
            "mode": "pseudonymize",
            "salt": "test_salt",
            "output_dir": tempfile.mkdtemp(),
        })
        result2 = op2.run({"path": temp_dicom_file})
        ds2 = pydicom.dcmread(result2["deid_path"])

        assert ds1.PatientName == ds2.PatientName
        assert ds1.PatientID == ds2.PatientID

    def test_different_salt_different_result(self, temp_dicom_file):
        """Different salt should produce different pseudonym."""
        op1 = DICOMDeidentifier({
            "mode": "pseudonymize",
            "salt": "salt1",
            "output_dir": tempfile.mkdtemp(),
        })
        result1 = op1.run({"path": temp_dicom_file})
        ds1 = pydicom.dcmread(result1["deid_path"])

        op2 = DICOMDeidentifier({
            "mode": "pseudonymize",
            "salt": "salt2",
            "output_dir": tempfile.mkdtemp(),
        })
        result2 = op2.run({"path": temp_dicom_file})
        ds2 = pydicom.dcmread(result2["deid_path"])

        assert ds1.PatientName != ds2.PatientName


class TestDICOMDeidentifierDateShift:
    """Test date_shift mode."""

    def test_date_shift(self, temp_dicom_file):
        op = DICOMDeidentifier({
            "mode": "date_shift",
            "date_shift_days": 100,
            "output_dir": tempfile.mkdtemp(),
        })
        result = op.run({"path": temp_dicom_file})

        ds = pydicom.dcmread(result["deid_path"])
        assert ds.StudyDate == "20240424"  # 20240115 + 100 days
        assert ds.PatientBirthDate == "19900425"  # 19900115 + 100 days

    def test_date_shift_preserves_interval(self, temp_dicom_file):
        """Date shift should preserve relative intervals between studies."""
        op = DICOMDeidentifier({
            "mode": "date_shift",
            "date_shift_days": 365,
            "output_dir": tempfile.mkdtemp(),
        })
        result = op.run({"path": temp_dicom_file})

        ds = pydicom.dcmread(result["deid_path"])
        # Check interval is preserved using actual dates
        from datetime import datetime
        study_date = datetime.strptime(str(ds.StudyDate), "%Y%m%d")
        birth_date = datetime.strptime(str(ds.PatientBirthDate), "%Y%m%d")
        shifted_interval = (study_date - birth_date).days

        original_study = datetime(2024, 1, 15)
        original_birth = datetime(1990, 1, 15)
        original_interval = (original_study - original_birth).days
        assert shifted_interval == original_interval

    def test_pseudonymize_with_date_shift(self, temp_dicom_file):
        """date_shift mode should also pseudonymize non-date fields."""
        op = DICOMDeidentifier({
            "mode": "date_shift",
            "date_shift_days": 100,
            "salt": "test_salt",
            "output_dir": tempfile.mkdtemp(),
        })
        result = op.run({"path": temp_dicom_file})

        ds = pydicom.dcmread(result["deid_path"])
        assert str(ds.PatientName).startswith("ANON_")
        # InstitutionName is SH VR (max 16 chars), so hash may be truncated
        assert str(ds.InstitutionName) != "Test Hospital"


class TestDICOMDeidentifierKeepTags:
    """Test keep_tags whitelist."""

    def test_keep_patient_sex(self, temp_dicom_file):
        op = DICOMDeidentifier({
            "mode": "remove",
            "keep_tags": ["PatientSex"],
            "output_dir": tempfile.mkdtemp(),
        })
        result = op.run({"path": temp_dicom_file})

        ds = pydicom.dcmread(result["deid_path"])
        assert ds.PatientSex == "M"
        assert ds.PatientName == ""  # Still removed


class TestDICOMDeidentifierDirectory:
    """Test directory batch processing."""

    def test_deidentify_directory(self, temp_dicom_file):
        """Test processing a directory with multiple DICOM files."""
        # Create a temp directory with the sample file
        temp_dir = tempfile.mkdtemp()
        dicom_dir = os.path.join(temp_dir, "dicom")
        os.makedirs(dicom_dir)

        # Copy sample to multiple files
        for i in range(3):
            ds = pydicom.dcmread(temp_dicom_file)
            ds.SOPInstanceUID = generate_uid()
            ds.save_as(os.path.join(dicom_dir, f"file_{i}.dcm"))

        op = DICOMDeidentifier({"mode": "remove", "output_dir": tempfile.mkdtemp()})
        result = op.run({"path": dicom_dir})

        assert "error" not in result
        assert os.path.isdir(result["deid_path"])

        # Check all files were processed
        output_files = list(Path(result["deid_path"]).rglob("*.dcm"))
        assert len(output_files) == 3

        # Verify one file
        ds = pydicom.dcmread(str(output_files[0]))
        assert ds.PatientName == ""


class TestDeidAuditLogger:
    """Test audit logger."""

    def test_save_audit(self):
        logger = DeidAuditLogger(log_dir=tempfile.mkdtemp())
        audit = {
            "source": "/path/to/file.dcm",
            "mode": "remove",
            "modifications": [{"tag": "(0010,0010)", "keyword": "PatientName", "original": "John", "new": ""}],
        }
        filepath = logger.save(audit, "test_audit.json")

        assert os.path.exists(filepath)
        import json
        with open(filepath) as f:
            loaded = json.load(f)
        assert loaded["source"] == "/path/to/file.dcm"

    def test_default_filename(self):
        logger = DeidAuditLogger(log_dir=tempfile.mkdtemp())
        audit = {"mode": "remove", "modifications": []}
        filepath = logger.save(audit)

        assert os.path.exists(filepath)
        assert filepath.endswith(".json")
        assert "deid_audit_" in filepath
