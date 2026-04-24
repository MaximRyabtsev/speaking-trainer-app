from __future__ import annotations

import ast
import json
import re
import subprocess
from dataclasses import dataclass

from speaking_trainer.config.settings import AppSettings
from speaking_trainer.utils.subprocess_runner import assert_executable_file


class LlamaCppError(RuntimeError):
    pass


@dataclass(frozen=True)
class _LlamaAttempt:
    name: str
    args: list[str]


@dataclass(frozen=True)
class _LlamaProcessResult:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool

    @property
    def combined_output(self) -> str:
        return (self.stdout or "") + "\n" + (self.stderr or "")


class LocalLlamaCppAdapter:
    """Finite one-shot local question generation through llama.cpp.

    The adapter deliberately performs ONE model call per Generate Questions
    action. It never asks the model to rewrite/repair its own output because
    small chat models can fall into self-repair loops and keep creating new
    lists. Any repair after the model call is deterministic and local.
    """

    _GENERIC_FILLERS = [
        "How would you explain the main idea of this text in your own words?",
        "Which argument or point from the text do you find most important, and why?",
        "How would you describe the author’s perspective in a natural spoken answer?",
        "What example from the text would you use to explain the topic to someone else?",
        "What is your personal reaction to the ideas in this text, and why?",
        "How would you summarize the text for someone who has never read it before?",
        "Which idea from the text would be easiest for you to discuss in detail, and why?",
        "How could you connect the ideas in this text to real-world examples?",
        "What part of the text would you like to explore more deeply in a spoken answer?",
        "How would you compare the main idea of this text with a different point of view?",
    ]

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def generate_questions(self, source_text: str, count: int) -> list[str]:
        if count not in {5, 10}:
            raise ValueError("Question count must be 5 or 10.")
        assert_executable_file(self.settings.llama_cli_path, "llama-cli")
        assert_executable_file(self.settings.llm_model_path, "LLM model")

        output = self._call_llama(
            self._build_prompt(source_text[: self.settings.llm_max_chars], count),
            n_predict=520 if count == 10 else 340,
        )
        questions = self._parse_questions(output, count)
        if questions:
            return questions[:count]

        # Last-resort fallback. This prevents recursive model calls and also
        # prevents llama.cpp startup logs from becoming fake questions.
        return self._GENERIC_FILLERS[:count]

    def _call_llama(self, prompt: str, *, n_predict: int) -> str:
        base = [
            self.settings.llama_cli_path,
            "-m",
            self.settings.llm_model_path,
            "-p",
            prompt,
            "-n",
            str(n_predict),
            "--ctx-size",
            str(self.settings.llm_context_size),
            "--temp",
            "0.20",
            "--top-p",
            "0.85",
            "--repeat-penalty",
            "1.12",
            "--no-display-prompt",
        ]

        # Prefer disabling conversation mode completely. Some llama.cpp builds
        # enter a chat REPL for chat-template models unless this is specified.
        one_shot_attempts = [
            _LlamaAttempt("no-conversation-long", ["--no-conversation"]),
            _LlamaAttempt("no-conversation-short", ["-no-cnv"]),
            _LlamaAttempt("single-turn-long", ["--single-turn"]),
            _LlamaAttempt("single-turn-short", ["-st"]),
            _LlamaAttempt("legacy", []),
        ]

        errors: list[str] = []
        for attempt in one_shot_attempts:
            for log_args in (["--log-disable"], []):
                for gpu_args in (["-ngl", "999"], []):
                    command = base + attempt.args + log_args + gpu_args
                    result = self._run_llama_command(command, timeout=90)
                    combined = result.combined_output

                    if result.returncode not in (0, None) and not result.timed_out:
                        lowered = combined.lower()
                        if self._looks_like_unsupported_cli_arg(lowered):
                            errors.append(f"{attempt.name}: unsupported CLI flag combination.")
                            continue
                        if gpu_args:
                            errors.append(f"{attempt.name}: GPU args failed; retrying without -ngl.")
                            continue
                        raise LlamaCppError("llama-cli failed.\n\n" + combined[-5000:])

                    # First try to recover useful text even if llama-cli stayed
                    # in an interactive prompt and had to be killed. Some recent
                    # llama.cpp builds generate the answer, print ">", and then
                    # wait for the next user turn despite one-shot flags.
                    cleaned_stdout = self._strip_llama_noise(result.stdout)
                    if cleaned_stdout:
                        return cleaned_stdout

                    # Most builds put model text on stdout. This fallback exists
                    # only for builds that write everything to one stream. The
                    # parser still rejects technical logs and meta instructions.
                    cleaned_combined = self._strip_llama_noise(combined)
                    if cleaned_combined:
                        return cleaned_combined

                    if result.timed_out:
                        errors.append(
                            f"{attempt.name}: generated no parseable output before timeout; "
                            "llama-cli likely stayed in interactive mode."
                        )
                        continue

                    errors.append(f"{attempt.name}: empty model output.")

        raise LlamaCppError("llama-cli could not run in one-shot mode.\n\n" + "\n".join(errors[-10:]))

    @staticmethod
    def _run_llama_command(command: list[str], *, timeout: int) -> _LlamaProcessResult:
        """Run llama-cli without allowing it to take over the terminal.

        Newer llama.cpp builds can auto-enable conversation mode for models with
        chat templates. In that state the process may correctly generate an
        answer and then wait at a `>` prompt. subprocess.run(..., timeout=...)
        leaves the UI waiting until the timeout, and if stdout is not isolated
        the user sees the REPL prompt.

        We therefore pipe stdin/stdout/stderr, immediately provide `/exit` for
        any later REPL prompt, and close stdin. If a build still refuses to exit,
        we kill it and keep the captured partial output so the JSON parser can
        use the answer that was already generated.
        """
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout, stderr = proc.communicate(input="/exit\n/exit\n", timeout=timeout)
            return _LlamaProcessResult(
                returncode=proc.returncode,
                stdout=stdout or "",
                stderr=stderr or "",
                timed_out=False,
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return _LlamaProcessResult(
                returncode=proc.returncode,
                stdout=stdout or "",
                stderr=stderr or "",
                timed_out=True,
            )

    @staticmethod
    def _looks_like_unsupported_cli_arg(lowered_output: str) -> bool:
        return any(
            token in lowered_output
            for token in [
                "unknown argument",
                "invalid argument",
                "error: unrecognized",
                "unknown option",
                "unrecognized option",
                "invalid option",
            ]
        )

    @staticmethod
    def _build_prompt(source_text: str, count: int) -> str:
        return (
            "You are an English speaking-practice coach.\n"
            "Create prompts that make the user talk, explain, compare, summarize, and give opinions.\n\n"
            f"Generate exactly {count} open-ended speaking practice QUESTIONS based on the text below.\n\n"
            "Hard rules:\n"
            "- English only.\n"
            f"- Output exactly {count} items, no more and no fewer.\n"
            "- Every item must be a natural question and must end with a question mark.\n"
            "- Do NOT output statements, summaries, facts, categories, numbering, markdown, or commentary.\n"
            "- Do NOT explain your process, rewrite the task, or generate a second list.\n"
            "- Stop immediately after the closing JSON bracket.\n"
            "- Do NOT ask factual quiz questions like 'What did the author say?'\n"
            "- Prefer broad questions that invite a 30-90 second spoken answer.\n"
            "- The questions should help the user practice explaining the ideas in their own words.\n"
            "- Output only a valid JSON array of strings.\n\n"
            "Good style examples:\n"
            "[\n"
            '  "How would you explain the main idea of this text in your own words?",\n'
            '  "Which argument from the text do you find most convincing, and why?"\n'
            "]\n\n"
            "Text:\n"
            '"""\n'
            + source_text
            + '\n"""\n\n'
            "JSON array:"
        ).strip()

    @classmethod
    def _parse_questions(cls, output: str, count: int) -> list[str]:
        candidates: list[str] = []
        text = cls._strip_llama_noise(output)

        json_array = cls._extract_json_array(text)
        if json_array is not None:
            try:
                parsed = json.loads(json_array)
                if isinstance(parsed, list):
                    candidates.extend(str(item).strip() for item in parsed)
            except json.JSONDecodeError:
                pass

        if not candidates:
            candidates.extend(cls._extract_quoted_strings(text))

        if not candidates:
            candidates.extend(cls._parse_line_questions(text))

        cleaned = cls._clean_questions(candidates)
        if cleaned:
            return cls._complete_with_generic_questions(cleaned, count)
        return []

    @classmethod
    def _strip_llama_noise(cls, text: str) -> str:
        if not text:
            return ""

        normalized = text.replace("\r", "\n")
        if "JSON array:" in normalized:
            # If the prompt was echoed, generated answer starts after the last
            # marker. This also removes the example questions inside the prompt.
            normalized = normalized.split("JSON array:", 1)[-1]

        lines: list[str] = []
        for raw in normalized.splitlines():
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith("> "):
                stripped = stripped[2:].strip()
            lower = stripped.lower()
            if cls._is_technical_noise(stripped):
                continue
            if lower.startswith(("loading model", "build", "model", "modalities", "available commands")):
                continue
            if stripped.startswith(("▄▄", "██", "▀▀")):
                continue
            if stripped in {">", "...", "```", "```json"}:
                continue
            if stripped.startswith("[") and "prompt:" in lower and "generation:" in lower:
                continue
            lines.append(stripped)
        return "\n".join(lines).strip()

    @staticmethod
    def _extract_json_array(text: str) -> str | None:
        start = text.find("[")
        while start != -1:
            depth = 0
            in_string = False
            escape = False
            for index in range(start, len(text)):
                ch = text[index]
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : index + 1]
                        if '"' in candidate:
                            return candidate
                        break
            start = text.find("[", start + 1)
        return None

    @staticmethod
    def _extract_quoted_strings(text: str) -> list[str]:
        items: list[str] = []
        for match in re.finditer(r'"((?:[^"\\]|\\.){8,})"', text, flags=re.DOTALL):
            value = match.group(1)
            try:
                value = ast.literal_eval('"' + value + '"')
            except Exception:
                value = value.replace('\\"', '"')
            items.append(str(value).strip())
        return items

    @staticmethod
    def _parse_line_questions(text: str) -> list[str]:
        items: list[str] = []
        for raw in text.splitlines():
            line = re.sub(r"^[-*•\s]+", "", raw.strip())
            line = re.sub(r"^\d+[.)]\s*", "", line).strip(" ,'`[]")
            line = line.strip('"')
            if len(line) >= 12:
                items.append(line)
        return items

    @classmethod
    def _clean_questions(cls, candidates: list[str]) -> list[str]:
        seen: set[str] = set()
        questions: list[str] = []
        for item in candidates:
            q = re.sub(r"\s+", " ", item).strip("-•* `\t\n\r,[]")
            q = q.strip('"')
            if not q or len(q) < 12:
                continue
            if cls._is_technical_noise(q) or cls._is_meta_or_recursive_instruction(q):
                continue

            has_question_shape = q.endswith("?") or re.match(
                r"(?i)^(how|what|why|which|where|when|who|can|could|would|do|does|did|is|are|if|in what way)\b",
                q,
            )
            if not has_question_shape:
                continue
            if not q.endswith("?"):
                q += "?"
            if cls._is_technical_noise(q) or cls._is_meta_or_recursive_instruction(q):
                continue
            key = q.lower()
            if key not in seen:
                seen.add(key)
                questions.append(q)
        return questions

    @classmethod
    def _complete_with_generic_questions(cls, questions: list[str], count: int) -> list[str]:
        completed = list(questions)
        seen = {q.lower() for q in completed}
        for filler in cls._GENERIC_FILLERS:
            if len(completed) >= count:
                break
            if filler.lower() not in seen:
                completed.append(filler)
                seen.add(filler.lower())
        return completed[:count]

    @staticmethod
    def _is_meta_or_recursive_instruction(text: str) -> bool:
        lower = text.strip().lower()
        if not lower:
            return True
        forbidden_phrases = [
            "generate exactly",
            "output only",
            "valid json",
            "json array",
            "rewrite the previous",
            "previous output",
            "hard rules",
            "good style examples",
            "text below",
            "based on the text below",
            "here are",
            "i will",
            "sure,",
            "certainly",
            "as an ai",
        ]
        return any(phrase in lower for phrase in forbidden_phrases)

    @staticmethod
    def _is_technical_noise(text: str) -> bool:
        lower = text.strip().lower()
        if not lower:
            return True

        technical_tokens = [
            "ggml_",
            "llama_",
            "llm_load_",
            "metal",
            "mtl0",
            "apple m1",
            "gpu name",
            "tensor api",
            "residency set",
            "loaded in ",
            "using embedded",
            "build:",
            "modalities:",
            "available commands",
            "prompt:",
            "generation:",
            "sampler",
            "token",
            "ctx_size",
            "kv cache",
            "n_ctx",
            "n_batch",
            "mem required",
            "main:",
            "system_info",
            "print_info",
        ]
        if any(token in lower for token in technical_tokens):
            return True
        if re.search(r"\b(ms|t/s|mb|mib|gib)\b", lower):
            return True
        if re.match(r"^[a-z0-9_]+:\s", lower):
            return True
        return False
