# YAMII モデレーション機能 設計ドキュメント

## 概要

YAMIIは、やみすきーのAI自動モデレーション支援システム。通報された投稿について、利用規約・モデレーション原則に基づき違反の有無を判定する。

**重要**: YAMIIの判定は参考情報であり、最終的な処分は人間のモデレーターが決定する。

---

## 背景

### 改定の経緯（2026年1月22日）

ユーザーからの批判を受け、yamisskey-hub-starlightにおいて利用規約とモデレーション原則を全面改定した。

**指摘された問題点**:
1. **論理的矛盾**: 「表現の自由優先」と「他者を害さない限り」が両立不能
2. **曖昧な概念**: 「精神的資源」など定義不明確な概念による恣意的運用の懸念
3. **ASD対応不足**: 字義通りに解釈できないルールは、ASD当事者にとって予測不可能

**解決方針**: 倫理的原則に基づく厳格解釈（罪刑法定主義的アプローチ）
- 禁止事項は限定列挙（列挙されていない行為は禁止されない）
- 類推解釈・拡大解釈の禁止
- 運営者にも平等適用
- DAO投票による改定手続き

### 文書階層

```
YAMI DAO（主権者）
    │
    ▼
利用規約（term.md）← 法律相当
├── 4つの倫理的原則（全会一致で改定）
├── 禁止事項の大枠（2/3で追加）
├── 運営体制（YAMIIの役割含む）
└── 改定手続き
    │
    ▼
モデレーション原則（moderation.md）← 施行規則相当（過半数で改定）
├── 禁止事項の詳細（第1条〜第7条）
├── 許容事項（第8条〜第9条）
├── 処分手続き（第10条〜第13条）
├── 運用規則（第14条〜第15条）
├── 解釈規則（第16条〜第18条）
└── 例外規定（第19条）
```

---

## 4つの倫理的原則

すべてのモデレーション判定は、以下の原則に基づく：

| 原則 | 内容 |
|------|------|
| **自律尊重** | ユーザーは自己の意思に基づいて行動する権利を有する |
| **危害原則** | 他者に具体的な危害を与える場合に限り制限される |
| **明示性** | 禁止される行為は明示的に列挙。列挙されていない行為は禁止されない |
| **平等適用** | 運営者を含むすべてのユーザーに平等に適用 |

---

## YAMIIの役割（利用規約 第5条2項）

```
1. 判定業務: 通報された投稿について、本規約およびモデレーション原則に基づき、違反の有無を判定する
2. 判定基準: 判定は、明示性原則に従い、列挙された禁止事項との照合によってのみ行う。類推解釈および拡大解釈は行わない
3. 判定結果: 「違反」「非違反」「判定不能」のいずれかを出力する
4. 人間による最終判断: YAMIIの判定は参考情報であり、最終的な処分は人間のモデレーターが決定する
```

### 設計原則

1. **Moderation as Code**: 運用フローは実装そのもの（プロンプト、判定ロジック）として表現
2. **厳格な照合**: 禁止事項リストとの機械的照合のみ。「空気を読む」判定は禁止
3. **透明性**: 判定理由は常に「第X条Y項に該当」の形式で出力
4. **判定不能の許容**: 曖昧なケースは「判定不能」として人間に委ねる

---

## 実装タスク

### Phase 1: 禁止事項データの構造化 ✅ 優先度: 高

モデレーション原則の禁止事項（第1条〜第7条）を機械可読形式で構造化する。

**ファイル**: `yamii/domain/moderation/prohibitions.py` または `data/prohibitions.yaml`

```yaml
prohibited_acts:
  # 第1条 自律侵害行為
  - id: "1-1"
    article: "第1条1項"
    category: "自律侵害"
    name: "返信の強要"
    description: "「返信しないと〜する」「無視するな」等、返信を強要する表現"
    keywords: ["返信しないと", "無視するな", "返事して", "既読無視"]
    examples:
      - "返信しないと死ぬ"
      - "なんで無視するの？返事して"
    non_examples:
      - "返信くれると嬉しいな"
      - "時間あるときに返事ください"

  - id: "1-2"
    article: "第1条2項"
    category: "自律侵害"
    name: "行動の束縛"
    description: "「〇〇時まで起きていて」「他の人と話すな」等、他者の行動を束縛する表現"
    keywords: ["起きていて", "他の人と話すな", "〜するな", "〜しないで"]
    examples:
      - "深夜2時まで起きていてね"
      - "他の人と仲良くしないで"
    non_examples:
      - "できれば起きていてほしいな"
      - "寂しいけど仕方ないね"

  - id: "1-3"
    article: "第1条3項"
    category: "自律侵害"
    name: "接触拒否の無視"
    description: "相手が明示的に距離を置く意思を示した後も、接触を続ける行為"
    requires_context: true  # 過去のやり取りの確認が必要
    examples:
      - "（ブロックされた後に別アカウントで接触）"
      - "（「話しかけないで」と言われた後も繰り返しメンション）"

  - id: "1-4"
    article: "第1条4項"
    category: "自律侵害"
    name: "同調の強制"
    description: "自己の感情表現への同調を他者に強制する行為"
    keywords: ["わかるでしょ", "同じ気持ちになって", "理解しろ"]
    examples:
      - "私の気持ちがわからないの？理解しろよ"
    non_examples:
      - "この気持ち、わかってくれる人いるかな"

  # 第2条 脅迫的行為
  - id: "2-1"
    article: "第2条1項"
    category: "脅迫"
    name: "脅迫的支援要求"
    description: "「〇〇してくれないと死ぬ」「助けてくれないなら自傷する」等の表現"
    keywords: ["してくれないと死ぬ", "助けてくれないなら", "〜しないと自傷"]
    high_priority: true
    examples:
      - "話聞いてくれないと死ぬ"
      - "助けてくれないなら手首切る"
    non_examples:
      - "死にたい気持ちがある"
      - "辛くて自傷してしまった"

  - id: "2-2"
    article: "第2条2項"
    category: "脅迫"
    name: "罪悪感の付与"
    description: "支援を断った相手を責める、または罪悪感を与える行為"
    requires_context: true
    examples:
      - "あなたが話聞いてくれなかったから悪化した"
      - "見捨てるんだ、冷たいね"

  - id: "2-3"
    article: "第2条3項"
    category: "脅迫"
    name: "試し行為"
    description: "「私のことを本当に心配しているなら〜してくれるはず」等、相手を試す表現"
    keywords: ["本当に心配しているなら", "〜してくれるはず", "愛しているなら"]
    examples:
      - "本当に私のこと心配してるなら今すぐ来てよ"
    non_examples:
      - "心配してくれてありがとう"

  - id: "2-4"
    article: "第2条4項"
    category: "脅迫"
    name: "脅迫・恐喝"
    description: "「〇〇しないと〜する」「〜を公開するぞ」等の脅迫・恐喝"
    high_priority: true
    keywords: ["しないと", "公開するぞ", "ばらすぞ", "晒す"]
    examples:
      - "言うこと聞かないとDM晒すぞ"
      - "別れるなら写真ばらまく"

  - id: "2-5"
    article: "第2条5項"
    category: "脅迫"
    name: "危害の示唆"
    description: "身体的または精神的危害を示唆する表現"
    high_priority: true
    keywords: ["殺す", "ころす", "痛い目", "後悔させる"]
    examples:
      - "お前殺すぞ"
      - "痛い目に遭わせてやる"

  # 第3条 権利侵害行為
  - id: "3-1"
    article: "第3条1項"
    category: "権利侵害"
    name: "プライバシー侵害"
    description: "他者の個人情報を本人の同意なく公開する行為"
    high_priority: true
    pii_detection: true  # PII検出との連携
    examples:
      - "〇〇さんの本名は△△で、住所は..."
      - "あの人の通院先は..."

  - id: "3-2"
    article: "第3条2項"
    category: "権利侵害"
    name: "名誉毀損"
    description: "特定個人に対する、事実に基づかない中傷"
    requires_context: true
    examples:
      - "〇〇は犯罪者だ（事実無根）"

  - id: "3-3"
    article: "第3条3項"
    category: "権利侵害"
    name: "なりすまし"
    description: "他者または運営者になりすまして投稿する行為"
    examples:
      - "（他人のアイコン・名前を使用して投稿）"
      - "運営です。アカウントを凍結します（偽）"

  - id: "3-4"
    article: "第3条4項"
    category: "権利侵害"
    name: "ハラスメント"
    description: "相手が明示的に拒否した後も執拗に接触を続ける行為、ストーキング行為、セクシュアルハラスメント"
    requires_context: true
    high_priority: true

  # 第4条 危害誘導行為
  - id: "4-1"
    article: "第4条1項"
    category: "危害誘導"
    name: "自殺・自傷の推奨"
    description: "自殺または自傷を推奨する表現"
    high_priority: true
    keywords: ["死ねば", "死んだ方が", "自傷しろ", "切れば"]
    examples:
      - "お前なんか死ねばいいのに"
      - "そんなに辛いなら死んだ方がいいよ"
    non_examples:
      - "死にたい（自己の感情表現）"
      - "自傷してしまった（報告）"

  - id: "4-2"
    article: "第4条2項"
    category: "危害誘導"
    name: "具体的方法の提示"
    description: "自殺または自傷の具体的方法を提示する行為"
    high_priority: true
    examples:
      - "〇〇という薬を△△錠飲めば..."
      - "首を吊るには..."

  - id: "4-3"
    article: "第4条3項"
    category: "危害誘導"
    name: "犯罪の教唆"
    description: "犯罪行為を教唆、幇助、または実行する行為"
    high_priority: true

  # 第5条 差別的行為
  - id: "5-1"
    article: "第5条1項"
    category: "差別"
    name: "差別的攻撃"
    description: "人種、国籍、民族、性別、性的指向、性自認、宗教、障害等を理由とした攻撃"
    keywords: ["〇〇人は", "ホモ", "レズ", "ガイジ", "池沼", "きちがい"]
    examples:
      - "〇〇人は日本から出ていけ"
      - "精神障害者は危険だ"
    non_examples:
      - "私はLGBTQ+です（自己開示）"

  - id: "5-2"
    article: "第5条2項"
    category: "差別"
    name: "排除の扇動"
    description: "特定の属性を持つ集団全体に対する侮辱または排除の扇動"
    keywords: ["〜は全員", "〜はみんな", "〜を排除"]

  # 第6条 運営妨害行為
  - id: "6-1"
    article: "第6条1項"
    category: "運営妨害"
    name: "虚偽の通報"
    description: "虚偽の内容による通報を繰り返す行為"
    requires_context: true

  - id: "6-2"
    article: "第6条2項"
    category: "運営妨害"
    name: "システム攻撃"
    description: "DDoS/DoS攻撃、不正アクセス、サーバーへの過負荷等"
    high_priority: true
    technical_detection: true  # 技術的検出との連携

  - id: "6-3"
    article: "第6条3項"
    category: "運営妨害"
    name: "スパム"
    description: "同一または類似の内容を短時間に大量投稿する行為（目安：1時間に10回以上）"
    technical_detection: true

  - id: "6-4"
    article: "第6条4項"
    category: "運営妨害"
    name: "運営者への脅迫"
    description: "運営者に対する脅迫または過度な要求"
    high_priority: true

  # 第7条 コンテンツ規制
  - id: "7-1"
    article: "第7条1項"
    category: "コンテンツ"
    name: "NSFW指定の不備"
    description: "性的、暴力的、またはその他センシティブなコンテンツをNSFW指定なしで投稿する行為"
    content_analysis: true

  - id: "7-2"
    article: "第7条2項"
    category: "コンテンツ"
    name: "未成年者保護違反"
    description: "未成年者が閲覧可能な状態で成人向けコンテンツを投稿する行為"
    content_analysis: true

  - id: "7-3"
    article: "第7条3項"
    category: "コンテンツ"
    name: "違法コンテンツ"
    description: "児童の性的搾取、リベンジポルノ、犯罪記録等の違法コンテンツの投稿"
    high_priority: true
    content_analysis: true

# 許容事項（第8条〜第9条）- これらは違反ではない
permitted_acts:
  - id: "8-1"
    article: "第8条1項"
    description: "「死にたい」「辛い」「消えたい」等の感情表現"

  - id: "8-2"
    article: "第8条2項"
    description: "「助けてほしい」「話を聞いてほしい」等の表現（強要を伴わない限り）"

  - id: "8-3"
    article: "第8条3項"
    description: "運営、他ユーザー、またはコミュニティに対する批判的意見の表明（事実に基づく限り）"

  - id: "8-4"
    article: "第8条4項"
    description: "ユーザー間の意見の相違、議論、論争"

  - id: "8-5"
    article: "第8条5項"
    description: "禁止事項に該当しない限り、他者が不快に感じる表現"
```

### Phase 2: モデレーションプロンプト設計 ✅ 優先度: 高

**ファイル**: `yamii/domain/moderation/prompt.py`

```python
MODERATION_SYSTEM_PROMPT = """
あなたはやみすきーのモデレーション判定システム「YAMII」です。

## あなたの役割
通報された投稿について、モデレーション原則に基づき違反の有無を判定します。

## 判定の原則

### 4つの倫理的原則
1. 自律尊重: ユーザーは自己の意思に基づいて行動する権利を有する
2. 危害原則: 他者に具体的な危害を与える場合に限り制限される
3. 明示性: 禁止される行為は明示的に列挙。列挙されていない行為は禁止されない
4. 平等適用: 運営者を含むすべてのユーザーに平等に適用

### 厳格解釈の原則
- 禁止事項リストに明示的に記載されている行為のみを違反と判定する
- 類推解釈は禁止: 「似ているから」という理由で違反と判定してはならない
- 拡大解釈は禁止: 禁止事項の範囲を広げて解釈してはならない
- 疑わしきは罰せず: 違反かどうか迷う場合は「判定不能」とする

### 許容される表現（違反ではない）
- 「死にたい」「辛い」「消えたい」等の感情表現
- 「助けてほしい」「話を聞いてほしい」等の表現（強要を伴わない限り）
- 批判的意見の表明（事実に基づく限り）
- 他者が不快に感じる表現（禁止事項に該当しない限り）

## 禁止事項一覧
{prohibitions}

## 出力形式
必ず以下のJSON形式で出力してください：

```json
{
  "judgment": "違反" | "非違反" | "判定不能",
  "violated_articles": ["第1条1項"],  // 違反の場合のみ
  "reasoning": "判定理由の説明",
  "confidence": 0.0-1.0
}
```

## 重要な注意
- 「違反」と判定する場合、必ず該当する条項を明示すること
- 禁止事項に明記されていない行為は「非違反」
- 文脈が不明で判断できない場合は「判定不能」
- あなたの個人的な価値観で判断してはならない
"""
```

**入力**:
```json
{
  "content": "通報された投稿内容",
  "context": {
    "reply_to": "返信先の投稿（あれば）",
    "mentions": ["メンション対象のユーザー"],
    "previous_interactions": "過去のやり取り（必要に応じて）"
  },
  "report_reason": "通報理由（任意）"
}
```

**出力**:
```json
{
  "judgment": "違反" | "非違反" | "判定不能",
  "violated_articles": ["第1条1項", "第2条3項"],
  "reasoning": "「返信しないと死ぬ」という表現は、第2条1項（脅迫的支援要求）に該当する。",
  "confidence": 0.85
}
```

### Phase 3: APIエンドポイント実装 ✅ 優先度: 中

**ファイル**: `yamii/api/routes/moderation.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from yamii.domain.moderation.service import ModerationService

router = APIRouter(prefix="/v1/moderation", tags=["moderation"])

class ModerationRequest(BaseModel):
    content: str
    context: Optional[dict] = None
    report_reason: Optional[str] = None

class ModerationResponse(BaseModel):
    judgment: str  # "違反" | "非違反" | "判定不能"
    violated_articles: list[str] = []
    reasoning: str
    confidence: float

@router.post("/judge", response_model=ModerationResponse)
async def judge_content(
    request: ModerationRequest,
    service: ModerationService = Depends()
):
    """
    通報された投稿を判定する

    - judgment: 違反/非違反/判定不能
    - violated_articles: 違反した条項（違反の場合のみ）
    - reasoning: 判定理由
    - confidence: 確信度 (0.0-1.0)
    """
    result = await service.judge(
        content=request.content,
        context=request.context,
        report_reason=request.report_reason
    )
    return result
```

### Phase 4: Misskey連携（将来） ✅ 優先度: 低

Misskeyの通報システムとの連携。Webhook受信またはAPI経由での連携を検討。

---

## 運用フロー

```
通報（Misskey）
    │
    ▼
YAMII判定 (/v1/moderation/judge)
    │
    ├── 違反 ────────────┐
    │                    │
    ├── 非違反 ──────────┼──▶ モデレーター確認
    │                    │
    └── 判定不能 ────────┘
                         │
                         ▼
                    処分決定（人間）
                         │
                         ▼
                    通知・記録
```

---

## ディレクトリ構造（提案）

```
yamii/
├── domain/
│   ├── moderation/          # 新規追加
│   │   ├── __init__.py
│   │   ├── prohibitions.py  # 禁止事項データ
│   │   ├── prompt.py        # システムプロンプト
│   │   └── service.py       # 判定ロジック
│   └── ...
├── api/
│   └── routes/
│       ├── moderation.py    # 新規追加
│       └── ...
└── ...
```

---

## 参照ドキュメント

### yamisskey-hub-starlight
- [利用規約](https://hub.yami.ski/reference/term/) - `src/content/docs/reference/term.md`
- [モデレーション原則](https://hub.yami.ski/reference/moderation/) - `src/content/docs/reference/moderation.md`

### 関連コミット（2026年1月22日）
- 利用規約: 4つの倫理的原則の明記、運営体制の再構築（YAMII導入）、DAO投票による規約改定手続きの導入
- モデレーション原則: 倫理的原則に基づく厳格解釈への移行、禁止事項の限定列挙、許容事項の明示

---

## 実装チェックリスト

- [ ] Phase 1: 禁止事項データの構造化
  - [ ] `yamii/domain/moderation/prohibitions.py` 作成
  - [ ] 第1条〜第7条の全項目をデータ化
  - [ ] 許容事項（第8条〜第9条）もデータ化

- [ ] Phase 2: モデレーションプロンプト設計
  - [ ] `yamii/domain/moderation/prompt.py` 作成
  - [ ] プロンプトのテスト（様々なケースで検証）

- [ ] Phase 3: APIエンドポイント実装
  - [ ] `yamii/domain/moderation/service.py` 作成
  - [ ] `yamii/api/routes/moderation.py` 作成
  - [ ] `yamii/api/main.py` にルーター追加
  - [ ] テスト作成

- [ ] Phase 4: Misskey連携
  - [ ] Webhook受信エンドポイント
  - [ ] 通知機能（Discord/Misskey DM）

---

## 改定履歴

- 2026-01-22: 初版作成
- 2026-01-22: 引き継ぎ用に全面改訂（禁止事項データ、実装チェックリスト追加）
