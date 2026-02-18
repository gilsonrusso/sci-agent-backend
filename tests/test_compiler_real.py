import asyncio
from app.services.compiler import compiler_service


async def test_real_compilation():
    print("Testing real compilation with Docker...")
    content = r"""
\documentclass{article}
\begin{document}
Hello from Real Test!
\end{document}
    """
    try:
        pdf_bytes = await compiler_service.compile_project("test-proj", content)
        print(f"Success! Generated PDF of size: {len(pdf_bytes)} bytes")
        # Save it to check
        with open("test_output.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("Saved to test_output.pdf")
    except Exception as e:
        print(f"Failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_real_compilation())
