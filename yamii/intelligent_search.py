"""
インテリジェント検索システム
知識グラフを構築し、過去の会話から関連トピックを検索
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

from .conversation_summary import ConversationSummary, ConversationSummaryStore


@dataclass
class KnowledgeNode:
    """知識グラフノード（トピック）"""
    id: str
    topic: str
    mention_count: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    related_summaries: List[str] = field(default_factory=list)  # サマリーID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "mention_count": self.mention_count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "related_summaries": self.related_summaries
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeNode":
        return cls(
            id=data["id"],
            topic=data["topic"],
            mention_count=data.get("mention_count", 0),
            first_seen=datetime.fromisoformat(data.get("first_seen", datetime.now().isoformat())),
            last_seen=datetime.fromisoformat(data.get("last_seen", datetime.now().isoformat())),
            related_summaries=data.get("related_summaries", [])
        )


@dataclass
class KnowledgeEdge:
    """知識グラフエッジ（トピック間の関連性）"""
    source_id: str
    target_id: str
    weight: float = 1.0  # 関連度
    co_occurrence_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "weight": self.weight,
            "co_occurrence_count": self.co_occurrence_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeEdge":
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            weight=data.get("weight", 1.0),
            co_occurrence_count=data.get("co_occurrence_count", 1)
        )


@dataclass
class KnowledgeGraph:
    """知識グラフ"""
    user_id: str
    nodes: Dict[str, KnowledgeNode] = field(default_factory=dict)  # topic -> node
    edges: List[KnowledgeEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGraph":
        return cls(
            user_id=data["user_id"],
            nodes={k: KnowledgeNode.from_dict(v) for k, v in data.get("nodes", {}).items()},
            edges=[KnowledgeEdge.from_dict(e) for e in data.get("edges", [])]
        )

    def add_topic(self, topic: str, summary_id: str) -> None:
        """トピックを追加"""
        if topic not in self.nodes:
            self.nodes[topic] = KnowledgeNode(
                id=f"node_{len(self.nodes)}",
                topic=topic
            )

        node = self.nodes[topic]
        node.mention_count += 1
        node.last_seen = datetime.now()
        if summary_id not in node.related_summaries:
            node.related_summaries.append(summary_id)

    def add_edge(self, topic1: str, topic2: str) -> None:
        """トピック間のエッジを追加"""
        if topic1 == topic2:
            return

        # 既存のエッジを探す
        for edge in self.edges:
            if (edge.source_id == topic1 and edge.target_id == topic2) or \
               (edge.source_id == topic2 and edge.target_id == topic1):
                edge.co_occurrence_count += 1
                edge.weight = min(edge.weight + 0.1, 1.0)
                return

        # 新しいエッジを追加
        self.edges.append(KnowledgeEdge(
            source_id=topic1,
            target_id=topic2
        ))

    def get_related_topics(self, topic: str, limit: int = 5) -> List[Tuple[str, float]]:
        """関連トピックを取得"""
        if topic not in self.nodes:
            return []

        related = []
        for edge in self.edges:
            if edge.source_id == topic:
                related.append((edge.target_id, edge.weight))
            elif edge.target_id == topic:
                related.append((edge.source_id, edge.weight))

        # 重みでソート
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:limit]


@dataclass
class SearchResult:
    """検索結果"""
    summary: ConversationSummary
    relevance_score: float
    matched_keywords: List[str]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id": self.summary.id,
            "short_summary": self.summary.short_summary,
            "relevance_score": self.relevance_score,
            "matched_keywords": self.matched_keywords,
            "timestamp": self.timestamp.isoformat(),
            "topics": self.summary.topics
        }


@dataclass
class ParsedQuery:
    """解析されたクエリ"""
    keywords: List[str]
    time_range: Optional[Tuple[datetime, datetime]] = None
    query_type: str = "general"  # general, topic, sentiment
    sentiment_filter: Optional[str] = None  # positive, neutral, negative


class IntelligentSearchEngine:
    """インテリジェント検索エンジン"""

    def __init__(self, summary_store: ConversationSummaryStore):
        self.summary_store = summary_store
        self._knowledge_graphs: Dict[str, KnowledgeGraph] = {}

        # 時間関連キーワード
        self._time_keywords = {
            "今日": lambda: (datetime.now().replace(hour=0, minute=0, second=0),
                           datetime.now()),
            "昨日": lambda: (datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=1),
                           datetime.now().replace(hour=0, minute=0, second=0)),
            "今週": lambda: (datetime.now() - timedelta(days=datetime.now().weekday()),
                           datetime.now()),
            "先週": lambda: (datetime.now() - timedelta(days=datetime.now().weekday() + 7),
                           datetime.now() - timedelta(days=datetime.now().weekday())),
            "今月": lambda: (datetime.now().replace(day=1, hour=0, minute=0, second=0),
                           datetime.now()),
            "最近": lambda: (datetime.now() - timedelta(days=7),
                           datetime.now()),
        }

        # センチメントキーワード
        self._sentiment_keywords = {
            "positive": ["嬉しい", "楽しい", "良かった", "幸せ"],
            "negative": ["悲しい", "辛い", "困った", "大変"],
            "neutral": []
        }

    def get_or_create_knowledge_graph(self, user_id: str) -> KnowledgeGraph:
        """知識グラフを取得または作成"""
        if user_id not in self._knowledge_graphs:
            self._knowledge_graphs[user_id] = KnowledgeGraph(user_id=user_id)
        return self._knowledge_graphs[user_id]

    def build_knowledge_graph(self, user_id: str) -> KnowledgeGraph:
        """
        ユーザーの過去サマリーから知識グラフを構築

        Args:
            user_id: ユーザーID

        Returns:
            KnowledgeGraph
        """
        graph = self.get_or_create_knowledge_graph(user_id)
        summaries = self.summary_store.get_user_summaries(user_id, limit=100)

        for summary in summaries:
            # トピックノードの追加
            for topic in summary.topics:
                graph.add_topic(topic, summary.id)

            # 同じサマリー内のトピック間にエッジを作成
            for i, topic1 in enumerate(summary.topics):
                for topic2 in summary.topics[i + 1:]:
                    graph.add_edge(topic1, topic2)

        return graph

    def parse_search_query(self, query: str) -> ParsedQuery:
        """
        検索クエリを解析

        Args:
            query: 検索クエリ

        Returns:
            ParsedQuery
        """
        keywords = []
        time_range = None
        sentiment_filter = None
        query_type = "general"

        # 時間範囲の検出
        for time_word, time_func in self._time_keywords.items():
            if time_word in query:
                time_range = time_func()
                query = query.replace(time_word, "")
                break

        # センチメントフィルタの検出
        for sentiment, words in self._sentiment_keywords.items():
            for word in words:
                if word in query:
                    sentiment_filter = sentiment
                    query = query.replace(word, "")
                    break

        # キーワード抽出（スペースで分割）
        keywords = [w.strip() for w in query.split() if w.strip() and len(w.strip()) > 1]

        # クエリタイプの判定
        if sentiment_filter:
            query_type = "sentiment"
        elif any(k in ["仕事", "恋愛", "家族", "健康"] for k in keywords):
            query_type = "topic"

        return ParsedQuery(
            keywords=keywords,
            time_range=time_range,
            query_type=query_type,
            sentiment_filter=sentiment_filter
        )

    def search_past_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[SearchResult]:
        """
        過去の会話を検索

        Args:
            user_id: ユーザーID
            query: 検索クエリ
            limit: 結果の最大数

        Returns:
            List[SearchResult]
        """
        # クエリ解析
        parsed = self.parse_search_query(query)

        # ユーザーのサマリーを取得
        summaries = self.summary_store.get_user_summaries(user_id, limit=100)

        results = []
        for summary in summaries:
            # 時間フィルタ
            if parsed.time_range:
                start, end = parsed.time_range
                if not (start <= summary.end_time <= end):
                    continue

            # センチメントフィルタ
            if parsed.sentiment_filter:
                if summary.sentiment.value != parsed.sentiment_filter:
                    continue

            # 関連性スコア計算
            score, matched = self._calculate_relevance(summary, parsed.keywords)

            if score > 0:
                # 時間減衰（古い会話は重み低下）
                days_old = (datetime.now() - summary.end_time).days
                time_decay = math.exp(-days_old / 30)  # 30日で約37%に減衰

                # 重要度を考慮
                final_score = score * time_decay * (0.5 + summary.importance_score * 0.5)

                results.append(SearchResult(
                    summary=summary,
                    relevance_score=final_score,
                    matched_keywords=matched,
                    timestamp=summary.end_time
                ))

        # スコア順でソート
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]

    def _calculate_relevance(
        self,
        summary: ConversationSummary,
        keywords: List[str]
    ) -> Tuple[float, List[str]]:
        """関連性スコアを計算"""
        score = 0.0
        matched = []

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # トピックマッチ（高重み）
            for topic in summary.topics:
                if keyword_lower in topic.lower():
                    score += 3.0
                    matched.append(keyword)
                    break

            # キーワードマッチ（中重み）
            for kw in summary.keywords:
                if keyword_lower in kw.lower():
                    score += 2.0
                    if keyword not in matched:
                        matched.append(keyword)
                    break

            # サマリーテキストマッチ（低重み）
            if keyword_lower in summary.short_summary.lower():
                score += 1.0
                if keyword not in matched:
                    matched.append(keyword)

            if keyword_lower in summary.detailed_summary.lower():
                score += 0.5

        return score, matched

    def suggest_related_topics(
        self,
        user_id: str,
        current_topic: str,
        limit: int = 3
    ) -> List[Tuple[str, float]]:
        """
        関連トピックを提案

        Args:
            user_id: ユーザーID
            current_topic: 現在のトピック
            limit: 結果の最大数

        Returns:
            List[(トピック, スコア)]
        """
        graph = self.get_or_create_knowledge_graph(user_id)

        # グラフが空なら構築
        if not graph.nodes:
            self.build_knowledge_graph(user_id)

        return graph.get_related_topics(current_topic, limit)

    def get_topic_history(self, user_id: str, topic: str) -> List[ConversationSummary]:
        """
        特定トピックの会話履歴を取得

        Args:
            user_id: ユーザーID
            topic: トピック

        Returns:
            List[ConversationSummary]
        """
        summaries = self.summary_store.get_user_summaries(user_id, limit=50)
        return [s for s in summaries if topic in s.topics]

    def get_knowledge_graph_visualization_data(self, user_id: str) -> Dict[str, Any]:
        """
        知識グラフの可視化用データを取得

        Args:
            user_id: ユーザーID

        Returns:
            Dict with nodes and edges for visualization
        """
        graph = self.get_or_create_knowledge_graph(user_id)

        nodes = [
            {
                "id": node.id,
                "label": node.topic,
                "size": min(node.mention_count * 5 + 10, 50)
            }
            for node in graph.nodes.values()
        ]

        edges = [
            {
                "source": edge.source_id,
                "target": edge.target_id,
                "weight": edge.weight
            }
            for edge in graph.edges
        ]

        return {
            "nodes": nodes,
            "edges": edges
        }

    def get_all_graphs_dict(self) -> Dict[str, Dict[str, Any]]:
        """全知識グラフを辞書形式で取得"""
        return {
            user_id: graph.to_dict()
            for user_id, graph in self._knowledge_graphs.items()
        }

    def load_from_dict(self, data: Dict[str, Dict[str, Any]]) -> None:
        """辞書から知識グラフを読み込み"""
        for user_id, graph_data in data.items():
            self._knowledge_graphs[user_id] = KnowledgeGraph.from_dict(graph_data)


class SemanticSearchEnhancer:
    """意味的検索の強化（将来のLLM統合用）"""

    def __init__(self):
        self._cache: Dict[str, List[str]] = {}

    def expand_query(self, query: str) -> List[str]:
        """
        クエリを意味的に拡張（将来はLLM使用）

        Args:
            query: 検索クエリ

        Returns:
            拡張されたキーワードリスト
        """
        # 現在は簡易的な同義語マッピング
        synonyms = {
            "仕事": ["職場", "会社", "キャリア", "業務"],
            "恋愛": ["彼氏", "彼女", "パートナー", "デート"],
            "お金": ["給料", "貯金", "金銭", "経済"],
            "健康": ["体調", "病気", "メンタル", "ストレス"],
            "家族": ["親", "子供", "両親", "兄弟"],
        }

        expanded = [query]
        for key, syns in synonyms.items():
            if key in query:
                expanded.extend(syns)

        return list(set(expanded))

    def rank_by_semantic_similarity(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        意味的類似度で結果をランク付け（将来実装）

        現在は関連性スコアでそのまま返す
        """
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)
