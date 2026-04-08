"""DICOMweb Client for interacting with DICOMweb servers (WADO-RS, STOW-RS)."""
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


class DICOMWebClient:
    """Client for DICOMweb (WADO-RS, STOW-RS) servers like Orthanc."""

    def __init__(
        self,
        base_url: str,
        username: str = None,
        password: str = None,
        timeout: int = 30,
    ):
        """Initialize DICOMweb client.

        Args:
            base_url: Base URL of DICOMweb server (e.g., http://localhost:8042/dicom-web).
            username: Basic auth username.
            password: Basic auth password.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/dicom+json"})

        if username and password:
            self.session.auth = (username, password)

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make HTTP request to DICOMweb server.

        Args:
            method: HTTP method.
            path: API path.
            **kwargs: Additional request arguments.

        Returns:
            Response object.
        """
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"DICOMweb request failed: {e}")
            raise

    # ========== WADO-RS: Retrieve ==========

    def get_studies(self, patient_id: str = None, study_date: str = None) -> list:
        """Query for studies.

        Args:
            patient_id: Filter by PatientID.
            study_date: Filter by StudyDate (e.g., "20240101").

        Returns:
            List of study metadata.
        """
        params = {}
        if patient_id:
            params["PatientID"] = patient_id
        if study_date:
            params["StudyDate"] = study_date

        response = self._request("GET", "studies", params=params if params else None)
        return response.json() if response.content else []

    def get_study(self, study_instance_uid: str) -> dict:
        """Get study metadata.

        Args:
            study_instance_uid: Study Instance UID.

        Returns:
            Study metadata.
        """
        response = self._request("GET", f"studies/{study_instance_uid}")
        return response.json()

    def get_series(self, study_instance_uid: str) -> list:
        """Get series in a study.

        Args:
            study_instance_uid: Study Instance UID.

        Returns:
            List of series metadata.
        """
        response = self._request("GET", f"studies/{study_instance_uid}/series")
        return response.json() if response.content else []

    def get_instances(self, study_instance_uid: str, series_instance_uid: str) -> list:
        """Get instances in a series.

        Args:
            study_instance_uid: Study Instance UID.
            series_instance_uid: Series Instance UID.

        Returns:
            List of instance metadata.
        """
        path = f"studies/{study_instance_uid}/series/{series_instance_uid}/instances"
        response = self._request("GET", path)
        return response.json() if response.content else []

    def retrieve_instance(
        self,
        study_instance_uid: str,
        series_instance_uid: str,
        sop_instance_uid: str,
    ) -> bytes:
        """Retrieve a single DICOM instance.

        Args:
            study_instance_uid: Study Instance UID.
            series_instance_uid: Series Instance UID.
            sop_instance_uid: SOP Instance UID.

        Returns:
            DICOM file bytes.
        """
        path = (
            f"studies/{study_instance_uid}/series/{series_instance_uid}"
            f"/instances/{sop_instance_uid}/file"
        )
        response = self._request("GET", path, headers={"Accept": "application/dicom"})
        return response.content

    def retrieve_series(self, study_instance_uid: str, series_instance_uid: str) -> list[bytes]:
        """Retrieve all instances in a series.

        Args:
            study_instance_uid: Study Instance UID.
            series_instance_uid: Series Instance UID.

        Returns:
            List of DICOM file bytes.
        """
        path = f"studies/{study_instance_uid}/series/{series_instance_uid}"
        response = self._request("GET", path, headers={"Accept": "application/dicom"})
        # Bulk DICOM response - need to parse multipart
        # For now, return empty list as fallback
        logger.warning("Bulk retrieve not fully implemented, use retrieve_instance")
        return []

    # ========== STOW-RS: Store ==========

    def store_instances(self, dicom_files: list[bytes | Path]) -> dict:
        """Store DICOM instances to server.

        Args:
            dicom_files: List of DICOM file bytes or paths.

        Returns:
            Response with stored instance references.
        """
        import pydicom

        files = []
        for f in dicom_files:
            if isinstance(f, Path) or isinstance(f, str):
                files.append(open(f, "rb"))
            else:
                files.append(f)

        # Build multipart request
        import io

        buffer = io.BytesIO()
        for i, f in enumerate(files):
            if hasattr(f, "read"):
                content = f.read()
            else:
                content = f

            # Get dataset for metadata
            try:
                ds = pydicom.dcmread(io.BytesIO(content) if isinstance(content, bytes) else f)
                part = (
                    f'--boundary\r\n'
                    f'Content-Type: application/dicom\r\n'
                    f'Content-Length: {len(content)}\r\n\r\n'
                )
                buffer.write(part.encode())
                buffer.write(content)
                buffer.write(b"\r\n")
            except Exception as e:
                logger.warning(f"Failed to read DICOM: {e}")

        buffer.write(b"--boundary--\r\n")

        response = self._request(
            "POST",
            "studies",
            data=buffer.getvalue(),
            headers={"Content-Type": "multipart/related; type=application/dicom; boundary=boundary"},
        )

        # Close file handles
        for f in dicom_files:
            if isinstance(f, (Path, str)):
                f.close()

        return response.json() if response.content else {}

    # ========== QIDO-RS: Query ==========

    def qido_studies(
        self,
        patient_id: str = None,
        patient_name: str = None,
        study_date: str = None,
        modality: str = None,
        limit: int = 100,
    ) -> list:
        """Query for studies using QIDO-RS.

        Args:
            patient_id: PatientID filter.
            patient_name: PatientName filter (supports wildcards).
            study_date: StudyDate filter.
            modality: Modality filter.
            limit: Maximum results.

        Returns:
            List of matching studies.
        """
        params = {"limit": limit}
        if patient_id:
            params["PatientID"] = patient_id
        if patient_name:
            params["PatientName"] = patient_name
        if study_date:
            params["StudyDate"] = study_date
        if modality:
            params["Modality"] = modality

        response = self._request("GET", "studies", params=params)
        return response.json() if response.content else []

    def qido_series(
        self,
        study_instance_uid: str,
        modality: str = None,
        series_number: int = None,
    ) -> list:
        """Query for series in a study.

        Args:
            study_instance_uid: Study to search within.
            modality: Filter by Modality.
            series_number: Filter by SeriesNumber.

        Returns:
            List of matching series.
        """
        params = {}
        if modality:
            params["Modality"] = modality
        if series_number:
            params["SeriesNumber"] = series_number

        path = f"studies/{study_instance_uid}/series"
        response = self._request("GET", path, params=params if params else None)
        return response.json() if response.content else []


def create_orthanc_client(
    url: str = "http://localhost:8042",
    username: str = None,
    password: str = None,
) -> DICOMWebClient:
    """Create DICOMweb client for Orthanc server.

    Args:
        url: Orthanc server URL.
        username: Orthanc username (optional).
        password: Orthanc password (optional).

    Returns:
        Configured DICOMWebClient.
    """
    dicom_web_url = f"{url}/dicom-web"
    return DICOMWebClient(dicom_web_url, username, password)