# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv
import os
from typing import List, Dict, Any, Tuple

from src.services.exceptions import ImportExportError
from src.services.logging_service import logging_service


logger = logging_service.get_logger(__name__)


class PromptImportExportService:
    """Service for handling prompt import and export operations."""

    def __init__(self):
        """Initialize the PromptImportExportService."""
        pass

    def export_to_csv(
        self, file_path: str, prompts: List[Tuple[int, Dict[str, Any]]]
    ) -> bool:
        """
        Export prompts to CSV format.

        Args:
            file_path (str): Path to the output file
            prompts (List[Tuple[int, Dict[str, Any]]]): List of prompts to export

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["title", "prompt", "note", "category", "tags", "favorite"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for prompt_id, prompt_info in prompts:
                    data = prompt_info["data"]
                    row = {
                        "title": data.get("title", ""),
                        "prompt": data.get("prompt", ""),
                        "note": data.get("note", ""),
                        "category": data.get("category", "No category"),
                        "tags": ", ".join(data.get("tags", [])),
                        "favorite": "Yes" if data.get("favorite", False) else "No",
                    }
                    writer.writerow(row)
            return True
        except Exception as exc:
            logger.error(
                "Failed to export prompts to CSV",
                extra={"event": "prompts.export.csv.failure", "resource_id": file_path},
                exc_info=exc,
            )
            raise ImportExportError(
                "Failed to export prompts to CSV.",
                context={"file_path": file_path},
            ) from exc

    def export_to_markdown(
        self, file_path: str, prompts: List[Tuple[int, Dict[str, Any]]]
    ) -> bool:
        """
        Export prompts to Markdown format.

        Args:
            file_path (str): Path to the output file
            prompts (List[Tuple[int, Dict[str, Any]]]): List of prompts to export

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(file_path, "w", encoding="utf-8") as mdfile:
                for prompt_id, prompt_info in prompts:
                    data = prompt_info["data"]
                    mdfile.write(f"# {data.get('title', 'Untitled')}\n\n")
                    mdfile.write(
                        f"**Category:** {data.get('category', 'No category')}\n"
                    )
                    mdfile.write(f"**Tags:** {', '.join(data.get('tags', []))}\n")
                    mdfile.write(
                        f"**Favorite:** {'Yes' if data.get('favorite', False) else 'No'}\n\n"
                    )
                    mdfile.write("## Prompt\n")
                    mdfile.write(f"{data.get('prompt', '')}\n\n")
                    if data.get("note"):
                        mdfile.write("## Note\n")
                        mdfile.write(f"{data.get('note', '')}\n\n")
                    mdfile.write("---\n\n")  # Separator
            return True
        except Exception as exc:
            logger.error(
                "Failed to export prompts to Markdown",
                extra={
                    "event": "prompts.export.markdown.failure",
                    "resource_id": file_path,
                },
                exc_info=exc,
            )
            raise ImportExportError(
                "Failed to export prompts to Markdown.",
                context={"file_path": file_path},
            ) from exc

    def import_from_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Import prompts from CSV format.

        Args:
            file_path (str): Path to the input file

        Returns:
            List[Dict[str, Any]]: List of imported prompts
        """
        prompts = []
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        title = (row.get("title") or "").strip()
                        prompt_text = (row.get("prompt") or "").strip()
                        if not title and not prompt_text:
                            continue  # Skip completely empty rows

                        favorite_raw = (row.get("favorite") or "No").strip().lower()
                        favorite = favorite_raw in ("yes", "true", "1")

                        tags_field = row.get("tags")
                        tags = (
                            [tag.strip() for tag in tags_field.split(",")]
                            if tags_field
                            else []
                        )

                        category = (
                            row.get("category") or "No category"
                        ).strip() or "No category"
                        note = (row.get("note") or "").strip()

                        prompts.append(
                            {
                                "title": title,
                                "prompt": prompt_text,
                                "note": note,
                                "category": category,
                                "tags": tags,
                                "favorite": favorite,
                            }
                        )
                    except Exception as row_error:
                        logger.warning(
                            "Skipping malformed CSV row",
                            extra={
                                "event": "prompts.import.csv.warning",
                                "resource_id": file_path,
                            },
                            exc_info=row_error,
                        )
                        continue
        except FileNotFoundError as exc:
            logger.error(
                "CSV import file not found",
                extra={
                    "event": "prompts.import.csv.not_found",
                    "resource_id": file_path,
                },
                exc_info=exc,
            )
            return prompts
        except Exception as exc:
            logger.error(
                "Failed to import prompts from CSV",
                extra={"event": "prompts.import.csv.failure", "resource_id": file_path},
                exc_info=exc,
            )
            raise ImportExportError(
                "Failed to import prompts from CSV.",
                context={"file_path": file_path},
            ) from exc
        return prompts

    def import_from_markdown(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Import prompts from Markdown format.

        Args:
            file_path (str): Path to the input file

        Returns:
            List[Dict[str, Any]]: List of imported prompts
        """
        prompts = []
        try:
            with open(file_path, "r", encoding="utf-8") as mdfile:
                content = mdfile.read()
                # Split by '---' separator, then process each block
                blocks = content.split("---")
                for block in blocks:
                    if not block.strip():
                        continue

                    lines = block.strip().split("\n")
                    current_prompt = {
                        "title": "",
                        "prompt": "",
                        "note": "",
                        "category": "No category",
                        "tags": [],
                        "favorite": False,
                    }
                    current_section = None

                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        if line.startswith("# "):  # Title
                            current_prompt["title"] = line[2:].strip()
                            current_section = "title"
                        elif line.startswith("## Prompt"):
                            current_section = "prompt"
                        elif line.startswith("## Note"):
                            current_section = "note"
                        elif line.startswith("**Category:**"):
                            current_prompt["category"] = line.replace(
                                "**Category:**", ""
                            ).strip()
                        elif line.startswith("**Tags:**"):
                            tags_str = line.replace("**Tags:**", "").strip()
                            current_prompt["tags"] = [
                                tag.strip()
                                for tag in tags_str.split(",")
                                if tag.strip()
                            ]
                        elif line.startswith("**Favorite:**"):
                            current_prompt["favorite"] = (
                                line.replace("**Favorite:**", "").strip().lower()
                                == "yes"
                            )
                        elif current_section == "prompt":
                            current_prompt["prompt"] += line + "\n"
                        elif current_section == "note":
                            current_prompt["note"] += line + "\n"

                    # Clean up trailing newlines
                    current_prompt["prompt"] = current_prompt["prompt"].strip()
                    current_prompt["note"] = current_prompt["note"].strip()

                    # Remove 'history' if it somehow exists in the imported data
                    if "history" in current_prompt:
                        del current_prompt["history"]

                    if current_prompt.get("title") or current_prompt.get(
                        "prompt"
                    ):  # Only add if it has some content
                        prompts.append(current_prompt)
        except FileNotFoundError as exc:
            logger.error(
                "Markdown import file not found",
                extra={
                    "event": "prompts.import.markdown.not_found",
                    "resource_id": file_path,
                },
                exc_info=exc,
            )
            return prompts
        except Exception as exc:
            logger.error(
                "Failed to import prompts from Markdown",
                extra={
                    "event": "prompts.import.markdown.failure",
                    "resource_id": file_path,
                },
                exc_info=exc,
            )
            raise ImportExportError(
                "Failed to import prompts from Markdown.",
                context={"file_path": file_path},
            ) from exc
        return prompts
