import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from fastapi import HTTPException


class CompilerService:
    def __init__(self, docker_image: str = "ghcr.io/xu-cheng/texlive-small"):
        self.docker_image = docker_image

    async def compile_project(self, project_id: str, content: str) -> bytes:
        """
        Compiles LaTeX content into a PDF using a Docker container.
        """
        # Create a temporary directory for this compilation job
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)

            # Write content to main.tex
            tex_file = work_dir / "main.tex"
            tex_file.write_text(content)

            # Ensure output directory exists (implicitly done by tempfile)

            # Docker command to run pdflatex
            # Mounting temp_dir to /workdir in container
            # Running as current user to avoid permission issues (optional, but good practice)
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{str(work_dir)}:/workdir",
                "-w",
                "/workdir",
                self.docker_image,
                "pdflatex",
                "-interaction=nonstopmode",
                "main.tex",
            ]

            try:
                # Run the command
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,  # We handle return code manually
                )

                # Check if PDF was created regardless of return code
                # Pdflatex often returns non-zero on warnings
                pdf_file = work_dir / "main.pdf"
                if pdf_file.exists() and pdf_file.stat().st_size > 0:
                    return pdf_file.read_bytes()

                if process.returncode != 0:
                    # Compilation failed AND no PDF
                    error_log = process.stdout.decode() + "\n" + process.stderr.decode()
                    print(f"Compilation Error: {error_log}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Compilation Failed:\n{error_log[-1000:]}",
                    )

                # Check if PDF was created
                pdf_file = work_dir / "main.pdf"
                if not pdf_file.exists():
                    raise HTTPException(
                        status_code=500, detail="PDF file was not generated."
                    )

                return pdf_file.read_bytes()

            except Exception as e:
                # Cleanup is handled by TemporaryDirectory, but re-raise exception
                if isinstance(e, HTTPException):
                    raise e
                raise HTTPException(status_code=500, detail=f"System Error: {str(e)}")


# Singleton instance
compiler_service = CompilerService()
