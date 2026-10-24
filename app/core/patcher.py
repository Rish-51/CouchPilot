"""Bottom-to-top byte offset patch applicator."""
import re
from typing import Dict, List, Optional, Tuple
from app.core.models import Patch, Target, TargetType


class Patcher:
    """Applies patches bottom-to-top by byte offset to preserve earlier indices."""

    @staticmethod
    def format_docstring(docstring_text: str, indent: str) -> str:
        """Format a docstring with consistent quotes and target indentation."""
        clean = docstring_text.strip()
        if clean.startswith('"""') and clean.endswith('"""'):
            clean = clean[3:-3].strip()
        elif clean.startswith("'''") and clean.endswith("'''"):
            clean = clean[3:-3].strip()

        lines = clean.split("\n")
        if len(lines) == 1:
            return f'{indent}"""{lines[0]}"""\n'

        formatted = [f'{indent}"""{lines[0]}']
        for line in lines[1:]:
            if line.strip():
                formatted.append(f"{indent}{line}")
            else:
                formatted.append("")
        formatted.append(f'{indent}"""\n')
        return "\n".join(formatted)

    @staticmethod
    def build_annotated_signature(
        original_sig: str,
        param_annotations: Dict[str, str],
        return_annotation: Optional[str] = None
    ) -> str:
        """Inject parameter and return type annotations into a signature string."""
        sig = original_sig.strip()
        if sig.endswith(":"):
            sig = sig[:-1].strip()

        # Find parameters parenthesis
        param_start = sig.find("(")
        param_end = sig.rfind(")")
        if param_start == -1 or param_end == -1 or param_end < param_start:
            return original_sig

        header = sig[:param_start + 1]
        raw_params = sig[param_start + 1:param_end].strip()
        trailer = sig[param_end:]

        if not raw_params:
            annotated_params = ""
        else:
            parts = [p.strip() for p in raw_params.split(",") if p.strip()]
            new_parts: List[str] = []
            for part in parts:
                # Check if param already has annotation
                if ":" in part:
                    new_parts.append(part)
                    continue

                # Check default value
                if "=" in part:
                    param_name, default_val = [x.strip() for x in part.split("=", 1)]
                    if param_name in param_annotations:
                        ann = param_annotations[param_name]
                        new_parts.append(f"{param_name}: {ann} = {default_val}")
                    else:
                        new_parts.append(part)
                else:
                    param_name = part.strip()
                    if param_name in param_annotations:
                        ann = param_annotations[param_name]
                        new_parts.append(f"{param_name}: {ann}")
                    else:
                        new_parts.append(part)
            annotated_params = ", ".join(new_parts)

        # Rebuild signature with closing parenthesis
        new_sig = f"{header}{annotated_params})"

        if return_annotation and return_annotation.strip():
            ret_type = return_annotation.strip()
            if ret_type.startswith("->"):
                ret_type = ret_type[2:].strip()
            new_sig += f" -> {ret_type}:"
        else:
            new_sig += ":"

        return new_sig

    def apply_patch_to_target(
        self,
        code: str,
        target: Target,
        patch: Patch
    ) -> str:
        """Apply a single patch to the target inside the code string."""
        code_bytes = code.encode("utf-8")

        # Determine signature slice
        # Target signature spans from target.start_byte to the end of header
        raw_sig_part = code_bytes[target.start_byte:target.end_byte].decode("utf-8", errors="replace")
        
        # Check if one-liner
        colon_pos = raw_sig_part.find(":")
        if colon_pos == -1:
            return code

        # Build replacement header
        if target.target_type == TargetType.CLASS:
            new_sig = target.signature if target.signature.endswith(":") else f"{target.signature}:"
        else:
            new_sig = self.build_annotated_signature(
                target.signature,
                patch.param_annotations,
                patch.return_annotation
            )
            if not new_sig.endswith(":"):
                new_sig = f"{new_sig}:"

        # Prepare docstring
        docstring_block = ""
        if patch.generated_docstring and target.missing_docstring:
            docstring_block = self.format_docstring(patch.generated_docstring, target.body_indentation)

        # Check if one-liner (i.e. statement exists on the same line after colon)
        after_colon_first_line = raw_sig_part[colon_pos + 1:].split("\n")[0]
        if after_colon_first_line.strip():
            # Body statement is on the same line
            body_stmt = after_colon_first_line.strip()
            replacement = f"{new_sig}\n{docstring_block}{target.body_indentation}{body_stmt}\n"
            new_bytes = (
                code_bytes[:target.start_byte] +
                replacement.encode("utf-8") +
                code_bytes[target.end_byte:]
            )
            return new_bytes.decode("utf-8", errors="replace")

        # Standard multi-line function or class
        # Insert docstring right after the newline of the header
        header_end_byte = target.start_byte + colon_pos + 1
        # Find newline after colon
        nl_pos = code_bytes.find(b"\n", header_end_byte)
        if nl_pos != -1:
            header_end_byte = nl_pos + 1

        replacement_header = f"{new_sig}\n{docstring_block}"
        new_bytes = (
            code_bytes[:target.start_byte] +
            replacement_header.encode("utf-8") +
            code_bytes[header_end_byte:]
        )
        return new_bytes.decode("utf-8", errors="replace")

    def apply_patches(
        self,
        code: str,
        target_patch_pairs: List[Tuple[Target, Patch]]
    ) -> str:
        """Sort targets by start_byte descending and apply edits bottom-to-top."""
        # Sort descending by start_byte to keep earlier offsets constant
        sorted_pairs = sorted(target_patch_pairs, key=lambda pair: pair[0].start_byte, reverse=True)
        current_code = code

        for target, patch in sorted_pairs:
            current_code = self.apply_patch_to_target(current_code, target, patch)

        return current_code
