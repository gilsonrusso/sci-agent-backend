import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from fastapi import HTTPException


class CompilerService:
    def __init__(
        self,
        docker_image: str = "registry.gitlab.com/islandoftex/images/texlive:latest",
    ):
        self.docker_image = docker_image

    async def compile_project(self, project_id: str, content: str) -> bytes:
        """
        Compiles LaTeX content into a PDF using a Docker container.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            tex_file = work_dir / "main.tex"

            # FIX 1: Forçar UTF-8 para garantir que textos em português não quebrem o compilador
            tex_file.write_text(content, encoding="utf-8")

            # FIX 2: Substituir pdflatex por latexmk.
            # Ele resolve automaticamente múltiplas passagens necessárias para artigos com citações.
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{str(work_dir)}:/workdir",
                "-w",
                "/workdir",
                self.docker_image,
                "latexmk",  # Ferramenta inteligente de build
                "-pdf",  # Força saída em PDF
                "-interaction=nonstopmode",  # Não trava pedindo input
                "main.tex",
            ]

            try:
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )

                pdf_file = work_dir / "main.pdf"

                # Se gerou o PDF e tem tamanho, retorna (mesmo que haja warnings não fatais)
                if pdf_file.exists() and pdf_file.stat().st_size > 0:
                    return pdf_file.read_bytes()

                # FIX 3: Capturar o log completo sem cortar a parte onde o erro real ocorreu
                if process.returncode != 0:
                    full_log = (
                        process.stdout.decode("utf-8", errors="replace")
                        + "\n"
                        + process.stderr.decode("utf-8", errors="replace")
                    )

                    # Imprime o log completo no console do backend para você investigar
                    print(f"Compilation Error Full Log:\n{full_log}")

                    # Retorna os últimos 4000 caracteres para o frontend (geralmente suficiente para ver o erro real)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Compilation Failed. Check backend logs for full details. Tail:\n{full_log[-4000:]}",
                    )

                raise HTTPException(
                    status_code=500, detail="PDF file was not generated."
                )

            except Exception as e:
                if isinstance(e, HTTPException):
                    raise e
                raise HTTPException(status_code=500, detail=f"System Error: {str(e)}")


# Singleton instance
compiler_service = CompilerService()
