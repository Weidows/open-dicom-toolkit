"""DICOMweb Operator - Load DICOM from remote DICOMweb server."""
import io
from typing import Any

from src.core import OperatorBase, OperatorMeta

try:
    import pydicom
except ImportError:
    pydicom = None


class DICOMWebOperator(OperatorBase):
    """Load DICOM files from DICOMweb server (Orthanc, etc.)."""

    name = "dicomweb_operator"
    version = "0.1.0"
    capabilities = ["read", "DICOMweb", "network"]
    input_schema = {
        "study_uid": "str",  # Study Instance UID
        "series_uid": "str",  # Optional: Series Instance UID
        "server_url": "str",
    }
    output_schema = {"dicom_data": "list", "metadata": "dict"}

    def __init__(self, config: dict):
        super().__init__(config)
        self.server_url = config.get("server_url")
        self.username = config.get("username")
        self.password = config.get("password")
        self.client = None

    def _get_client(self):
        """Get or create DICOMweb client."""
        if self.client is None:
            from .dicomweb_client import create_orthanc_client

            self.client = create_orthanc_client(
                url=self.server_url,
                username=self.username,
                password=self.password,
            )
        return self.client

    def run(self, ctx: dict) -> dict:
        """Load DICOM from DICOMweb server.

        Args:
            ctx: Must contain 'study_uid' and optionally 'server_url'.

        Returns:
            ctx with 'dicom_data' (list of pydicom.Dataset) and 'metadata'.
        """
        if pydicom is None:
            ctx["error"] = "pydicom not installed"
            return ctx

        study_uid = ctx.get("study_uid")
        if not study_uid:
            ctx["error"] = "No study_uid provided"
            return ctx

        # Get server URL from context or config
        server_url = ctx.get("server_url", self.server_url)
        if not server_url:
            ctx["error"] = "No server_url provided"
            return ctx

        try:
            client = self._get_client()
            client.base_url = server_url.rstrip("/") + "/dicom-web"

            # Get series if not specified
            series_uid = ctx.get("series_uid")
            if not series_uid:
                series = client.get_series(study_uid)
                if not series:
                    ctx["error"] = f"No series found in study {study_uid}"
                    return ctx
                series_uid = series[0].get("0020000E", {}).get("Value", [None])[0]

            # Get instances
            instances = client.get_instances(study_uid, series_uid)
            dicom_data = []

            for inst in instances:
                sop_uid = inst.get("00080018", {}).get("Value", [None])[0]
                if sop_uid:
                    data = client.retrieve_instance(study_uid, series_uid, sop_uid)
                    ds = pydicom.dcmread(io.BytesIO(data))
                    dicom_data.append(ds)

            ctx["dicom_data"] = dicom_data
            ctx["metadata"] = {
                "study_uid": study_uid,
                "series_uid": series_uid,
                "instance_count": len(dicom_data),
                "server_url": server_url,
            }

        except Exception as e:
            ctx["error"] = str(e)
            ctx["dicom_data"] = []

        return ctx


class DICOMWebStoreOperator(OperatorBase):
    """Store DICOM files to DICOMweb server."""

    name = "dicweb_store_operator"
    version = "0.1.0"
    capabilities = ["write", "DICOMweb", "network"]
    input_schema = {"dicom_data": "list", "server_url": "str"}
    output_schema = {"stored_count": "int", "response": "dict"}

    def __init__(self, config: dict):
        super().__init__(config)
        self.server_url = config.get("server_url")
        self.username = config.get("username")
        self.password = config.get("password")
        self.client = None

    def _get_client(self):
        """Get or create DICOMweb client."""
        if self.client is None:
            from .dicomweb_client import create_orthanc_client

            self.client = create_orthanc_client(
                url=self.server_url,
                username=self.username,
                password=self.password,
            )
        return self.client

    def run(self, ctx: dict) -> dict:
        """Store DICOM to DICOMweb server.

        Args:
            ctx: Contains 'dicom_data' (list of pydicom.Dataset) and 'server_url'.

        Returns:
            ctx with 'stored_count' and 'response'.
        """
        if pydicom is None:
            ctx["error"] = "pydicom not installed"
            return ctx

        dicom_data = ctx.get("dicom_data", [])
        if not dicom_data:
            ctx["stored_count"] = 0
            return ctx

        server_url = ctx.get("server_url", self.server_url)
        if not server_url:
            ctx["error"] = "No server_url provided"
            return ctx

        try:
            client = self._get_client()
            client.base_url = server_url.rstrip("/") + "/dicom-web"

            # Convert datasets to bytes
            dicom_bytes = []
            for ds in dicom_data:
                buffer = io.BytesIO()
                ds.save_as(buffer)
                dicom_bytes.append(buffer.getvalue())

            # Store
            response = client.store_instances(dicom_bytes)
            ctx["stored_count"] = len(dicom_bytes)
            ctx["response"] = response

        except Exception as e:
            ctx["error"] = str(e)
            ctx["stored_count"] = 0

        return ctx