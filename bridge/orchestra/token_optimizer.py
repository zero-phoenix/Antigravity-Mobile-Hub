"""
Token Optimizer & Context Efficiency Sentinel
Maximiza el rendimiento de tokens en el ecosistema Multi-Agente MAGI:
- Compresión semántica de salidas de consola (reducción del 95% de tokens basura).
- Payloads A2A (Agent-to-Agent) en formato Delta.
- Seguimiento de tokens consumidos, cacheados y ahorrados.
"""

import re
import time
from typing import Dict, Any, List, Optional

class TokenTracker:
    def __init__(self):
        self.session_start = time.time()
        self.gemini_input_tokens = 0
        self.gemini_output_tokens = 0
        self.gemini_cached_tokens = 0
        self.claude_tokens_estimated = 0
        self.codex_tokens_estimated = 0
        self.tokens_saved_by_compression = 0
        self.tokens_saved_by_cache = 0
        self.total_invocations = 0

    def record_gemini(self, input_tok: int, output_tok: int, cached_tok: int = 0):
        self.gemini_input_tokens += input_tok
        self.gemini_output_tokens += output_tok
        self.gemini_cached_tokens += cached_tok
        self.tokens_saved_by_cache += cached_tok
        self.total_invocations += 1

    def record_claude(self, prompt_text: str, response_text: str):
        toks = (len(prompt_text) + len(response_text)) // 4
        self.claude_tokens_estimated += toks
        self.total_invocations += 1

    def record_codex(self, prompt_text: str, response_text: str):
        toks = (len(prompt_text) + len(response_text)) // 4
        self.codex_tokens_estimated += toks
        self.total_invocations += 1

    def record_savings(self, original_chars: int, compressed_chars: int):
        saved = max(0, (original_chars - compressed_chars) // 4)
        self.tokens_saved_by_compression += saved

    def get_stats(self) -> Dict[str, Any]:
        total_used = (
            self.gemini_input_tokens
            + self.gemini_output_tokens
            + self.claude_tokens_estimated
            + self.codex_tokens_estimated
        )
        total_saved = self.tokens_saved_by_compression + self.tokens_saved_by_cache
        return {
            "total_tokens_used": total_used,
            "total_tokens_saved": total_saved,
            "savings_ratio": round(total_saved / max(1, total_used + total_saved) * 100, 1),
            "gemini": {
                "input": self.gemini_input_tokens,
                "output": self.gemini_output_tokens,
                "cached": self.gemini_cached_tokens,
            },
            "claude_estimated": self.claude_tokens_estimated,
            "codex_estimated": self.codex_tokens_estimated,
            "invocations": self.total_invocations,
            "uptime_seconds": round(time.time() - self.session_start),
        }

class TokenOptimizer:
    def __init__(self):
        self.tracker = TokenTracker()

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def compact_console_output(self, raw_output: str, max_lines: int = 35) -> str:
        """
        Comprime salidas largas de PowerShell, compiladores y suites de pruebas
        para no saturar la ventana de contexto de los modelos con texto redundante.
        Extrae solo el encabezado, líneas de error/falla con su contexto, y el resumen final.
        """
        if not raw_output:
            return ""

        original_len = len(raw_output)
        lines = raw_output.splitlines()

        if len(lines) <= max_lines and original_len <= 3000:
            return raw_output

        error_regex = re.compile(
            r"(error|fail|exception|fatal|traceback|panic|syntaxerror|cannot|warning|abort|denied|timed out)",
            re.IGNORECASE,
        )

        selected_indices = set()

        # Primeras líneas (comando y arranque)
        for i in range(min(6, len(lines))):
            selected_indices.add(i)

        # Últimas líneas (código de salida y resumen)
        for i in range(max(0, len(lines) - 10), len(lines)):
            selected_indices.add(i)

        # Líneas críticas con errores y su vecindario
        for idx, line in enumerate(lines):
            if error_regex.search(line):
                start = max(0, idx - 1)
                end = min(len(lines), idx + 2)
                for j in range(start, end):
                    selected_indices.add(j)

        sorted_indices = sorted(selected_indices)
        compressed_lines = []
        last_idx = -1

        for idx in sorted_indices:
            if last_idx != -1 and idx > last_idx + 1:
                omitted = idx - last_idx - 1
                compressed_lines.append(f"... [{omitted} líneas omitidas por Token Optimizer] ...")
            compressed_lines.append(lines[idx])
            last_idx = idx

        result = "\n".join(compressed_lines)
        self.tracker.record_savings(original_len, len(result))
        return result

    def build_a2a_delta(
        self,
        task_id: str,
        role: str,
        verdict: str,
        code_diff: str = "",
        evidence: str = "",
        files_modified: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Construye un payload Delta estructurado de baja huella de tokens
        para la comunicación entre agentes (Melchior -> Balthasar -> Casper).
        """
        compact_evidence = self.compact_console_output(evidence, max_lines=25)
        return {
            "task_id": task_id,
            "role": role,
            "verdict": verdict,
            "code_diff": code_diff[:4000] if len(code_diff) > 4000 else code_diff,
            "files_modified": files_modified or [],
            "evidence": compact_evidence,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

token_optimizer = TokenOptimizer()
