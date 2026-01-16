"""
PII（個人識別情報）匿名化サービス
OpenAIに送信前に個人情報をマスクし、応答後に復元する
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class AnonymizationResult:
    """匿名化結果"""

    anonymized_text: str
    mapping: dict[str, str]  # placeholder -> original
    pii_count: int


class PIIAnonymizer:
    """
    PII匿名化サービス

    検出対象:
    - 日本人名（漢字・ひらがな・カタカナ）
    - 電話番号
    - メールアドレス
    - 住所
    - 生年月日
    - マイナンバー
    - クレジットカード番号
    """

    def __init__(self):
        # PIIパターン定義（優先度順）
        self._patterns: list[tuple[str, str, re.Pattern]] = [
            # マイナンバー（12桁）
            (
                "MYNUMBER",
                "マイナンバー",
                re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
            ),
            # クレジットカード（16桁）
            (
                "CARD",
                "カード番号",
                re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
            ),
            # 電話番号（携帯・固定）
            (
                "PHONE",
                "電話番号",
                re.compile(
                    r"(?:0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4}|\d{3}[-\s]?\d{4}[-\s]?\d{4})"
                ),
            ),
            # メールアドレス
            (
                "EMAIL",
                "メール",
                re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
            ),
            # 生年月日（様々な形式）
            (
                "BIRTHDAY",
                "生年月日",
                re.compile(r"(?:19|20)\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?"),
            ),
            # 郵便番号
            ("ZIPCODE", "郵便番号", re.compile(r"〒?\d{3}[-]?\d{4}")),
            # 住所（都道府県から始まる）
            (
                "ADDRESS",
                "住所",
                re.compile(
                    r"(?:東京都|北海道|(?:京都|大阪)府|.{2,3}県)[^\s。、]+?(?:\d+[-ー]\d+[-ー]?\d*|丁目|番地?|号)"
                ),
            ),
        ]

        # 日本人名パターン（姓名の組み合わせ）
        self._name_patterns = [
            # 「〜さん」「〜様」「〜君」「〜ちゃん」で終わる名前
            re.compile(
                r"([一-龯ぁ-んァ-ン]{1,4})\s*([一-龯ぁ-んァ-ン]{1,4})\s*(?:さん|様|君|ちゃん|先生|氏)"
            ),
            # 「私は〜です」パターン
            re.compile(
                r"(?:私は|僕は|俺は|名前は)\s*([一-龯ぁ-んァ-ン]{2,8})(?:です|と申します|といいます)"
            ),
        ]

    def anonymize(self, text: str) -> AnonymizationResult:
        """
        テキスト内のPIIを匿名化

        Args:
            text: 元のテキスト

        Returns:
            AnonymizationResult: 匿名化されたテキストとマッピング
        """
        mapping: dict[str, str] = {}
        anonymized = text
        counters: dict[str, int] = {}

        # 標準PIIパターンの処理
        for pii_type, _, pattern in self._patterns:
            matches = list(pattern.finditer(anonymized))
            for match in reversed(matches):  # 後ろから置換（位置ずれ防止）
                original = match.group()
                counter = counters.get(pii_type, 0) + 1
                counters[pii_type] = counter
                placeholder = f"[{pii_type}_{counter}]"

                mapping[placeholder] = original
                anonymized = (
                    anonymized[: match.start()]
                    + placeholder
                    + anonymized[match.end() :]
                )

        # 名前パターンの処理
        for pattern in self._name_patterns:
            matches = list(pattern.finditer(anonymized))
            for match in reversed(matches):
                original = match.group()
                # 既にプレースホルダーが含まれている場合はスキップ
                if "[" in original:
                    continue

                counter = counters.get("NAME", 0) + 1
                counters["NAME"] = counter
                placeholder = f"[NAME_{counter}]"

                mapping[placeholder] = original
                anonymized = (
                    anonymized[: match.start()]
                    + placeholder
                    + anonymized[match.end() :]
                )

        return AnonymizationResult(
            anonymized_text=anonymized,
            mapping=mapping,
            pii_count=len(mapping),
        )

    def deanonymize(self, text: str, mapping: dict[str, str]) -> str:
        """
        プレースホルダーを元の値に復元

        Args:
            text: 匿名化されたテキスト
            mapping: プレースホルダー→元の値のマッピング

        Returns:
            str: 復元されたテキスト
        """
        result = text
        for placeholder, original in mapping.items():
            result = result.replace(placeholder, original)
        return result

    def detect_pii(self, text: str) -> list[dict[str, str]]:
        """
        テキスト内のPIIを検出（匿名化なし）

        Args:
            text: 検査対象テキスト

        Returns:
            List[Dict]: 検出されたPIIのリスト
        """
        detected = []

        for pii_type, label, pattern in self._patterns:
            for match in pattern.finditer(text):
                detected.append(
                    {
                        "type": pii_type,
                        "label": label,
                        "value": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                    }
                )

        return detected


# グローバルインスタンス
_anonymizer: PIIAnonymizer | None = None


def get_anonymizer() -> PIIAnonymizer:
    """匿名化サービスのシングルトンを取得"""
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = PIIAnonymizer()
    return _anonymizer


def anonymize_text(text: str) -> AnonymizationResult:
    """テキストを匿名化（便利関数）"""
    return get_anonymizer().anonymize(text)


def deanonymize_text(text: str, mapping: dict[str, str]) -> str:
    """テキストを復元（便利関数）"""
    return get_anonymizer().deanonymize(text, mapping)
