import pytest
from unittest.mock import MagicMock, patch
from app.services.compiler import CompilerService
from fastapi import HTTPException


# Mock Docker client or subprocess
@pytest.mark.asyncio
async def test_compile_project_success():
    service = CompilerService()

    # We'll patch subprocess.run to verify it calls docker
    with patch("subprocess.run") as mock_run:
        # Mock success response
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # We also need to mock pathlib.Path.write_text and exists/read_bytes
        # But since we use tempfile, it's easier to just let it write to /tmp (it's safe)
        # However, the docker command won't actually generate the PDF if we mock it.
        # So check_output will verify the PDF exists.

        # Let's mock the file existence check and read_bytes
        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_bytes", return_value=b"%PDF-1.4 mock"
        ):

            pdf_bytes = await service.compile_project(
                "project-123",
                "\\documentclass{article}\\begin{document}Test\\end{document}",
            )

            assert pdf_bytes == b"%PDF-1.4 mock"

            # Verify docker command
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "docker" in args
            assert "pdflatex" in args
            assert "ghcr.io/xu-cheng/texlive-small" in args


@pytest.mark.asyncio
async def test_compile_project_docker_failure():
    service = CompilerService()

    with patch("subprocess.run") as mock_run:
        # Mock failure
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = b"LaTeX Error"
        mock_process.stderr = b""
        mock_run.return_value = mock_process

        with pytest.raises(HTTPException) as exc_info:
            await service.compile_project("project-123", "invalid latex")

        assert exc_info.value.status_code == 400
        assert "Compilation Failed" in exc_info.value.detail
