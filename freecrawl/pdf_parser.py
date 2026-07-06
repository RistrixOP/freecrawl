"""
PDF content extraction via pymupdf (fitz).
Download PDF -> extract text -> markdown.
"""
import os, time, tempfile
from typing import Dict, Any, Optional
from .config import Config


class PDFParser:
    """Download and extract text from PDF files."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        os.makedirs(self.config.pdf_cache_dir, exist_ok=True)

    def parse(self, url: str, to_markdown: bool = True,
              include_images: bool = False, cache: bool = True) -> Dict[str, Any]:
        """Download a PDF and extract its text content.

        Args:
            url: URL to a PDF file
            to_markdown: Convert extracted text to markdown format
            include_images: Whether to attempt to extract images
            cache: Cache the extracted text

        Returns:
            Dict with extracted content
        """
        import fitz  # pymupdf
        import httpx

        start = time.time()
        pdf_path = None

        try:
            # Download the PDF
            client = httpx.Client(timeout=30, follow_redirects=True)
            response = client.get(url)

            if response.status_code != 200:
                return {
                    "error": f"HTTP {response.status_code} downloading PDF",
                    "url": url,
                    "elapsed": round(time.time() - start, 2),
                }

            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                # Might still be a PDF
                if not response.content[:5] == b"%PDF-":
                    return {
                        "error": "Response is not a PDF file",
                        "url": url,
                        "elapsed": round(time.time() - start, 2),
                    }

            # Save to temp file
            fd, pdf_path = tempfile.mkstemp(suffix=".pdf", dir=self.config.pdf_cache_dir)
            os.write(fd, response.content)
            os.close(fd)
            client.close()

            # Open with pymupdf
            doc = fitz.open(pdf_path)
            num_pages = len(doc)

            pages = []
            full_text = []

            for i in range(num_pages):
                page = doc[i]
                text = page.get_text()
                full_text.append(text)

                page_data = {
                    "page": i + 1,
                    "text": text,
                    "char_count": len(text),
                }

                if include_images:
                    images = page.get_images()
                    page_data["image_count"] = len(images)

                pages.append(page_data)

            doc.close()

            combined_text = "\n\n".join(full_text)

            result = {
                "url": url,
                "title": os.path.basename(url) or "Unknown",
                "num_pages": num_pages,
                "text": combined_text,
                "char_count": len(combined_text),
                "pages": pages,
                "elapsed": round(time.time() - start, 2),
            }

            if to_markdown:
                # Simple text-to-markdown conversion
                result["markdown"] = self._text_to_markdown(combined_text, url)

            if cache:
                # Cache result
                cache_path = os.path.join(
                    self.config.pdf_cache_dir,
                    f"{abs(hash(url))}.json"
                )
                import json
                with open(cache_path, 'w') as f:
                    json.dump({"url": url, "text": combined_text, "markdown": result.get("markdown", "")}, f)

            return result

        except ImportError as e:
            return {
                "error": f"pymupdf not available: {e}",
                "url": url,
                "elapsed": round(time.time() - start, 2),
            }
        except Exception as e:
            return {
                "error": str(e),
                "url": url,
                "elapsed": round(time.time() - start, 2),
            }
        finally:
            if pdf_path and os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except:
                    pass

    def _text_to_markdown(self, text: str, url: str = "") -> str:
        """Convert extracted text to basic markdown."""
        lines = text.split("\n")
        md_lines = []
        in_list = False
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            # Skip empty leading/trailing lines in certain contexts
            if not stripped:
                if in_list:
                    md_lines.append("")
                    in_list = False
                md_lines.append("")
                continue

            # Headers (based on font size heuristics - simplified)
            if stripped.isupper() and len(stripped) > 3 and len(stripped) < 80:
                md_lines.append(f"\n## {stripped}\n")
                continue

            # Bullet list detection
            if stripped.startswith("-") or stripped.startswith("•") or stripped.startswith("*"):
                md_lines.append(f"- {stripped.lstrip('-•* ')}")
                in_list = True
                continue

            # Numbered list
            if stripped[0].isdigit() and ". " in stripped[:5]:
                md_lines.append(stripped)
                in_list = True
                continue

            # Regular paragraph (join short lines)
            if stripped.endswith(".") or stripped.endswith(":") or stripped.endswith("!"):
                md_lines.append(stripped + "\n")
            else:
                md_lines.append(stripped)

        # Join and clean up excessive blank lines
        md = "\n".join(md_lines)
        import re
        md = re.sub(r'\n{3,}', '\n\n', md)
        return md.strip()

    def parse_local(self, filepath: str, to_markdown: bool = True) -> Dict[str, Any]:
        """Parse a local PDF file."""
        import fitz
        start = time.time()

        try:
            doc = fitz.open(filepath)
            num_pages = len(doc)
            full_text = []

            for i in range(num_pages):
                full_text.append(doc[i].get_text())

            doc.close()
            combined = "\n\n".join(full_text)

            result = {
                "filepath": filepath,
                "num_pages": num_pages,
                "text": combined,
                "char_count": len(combined),
                "elapsed": round(time.time() - start, 2),
            }

            if to_markdown:
                result["markdown"] = self._text_to_markdown(combined)

            return result
        except Exception as e:
            return {"error": str(e), "filepath": filepath}
