"""AI ヘルスチェックの TTL キャッシュのテスト"""

import pytest

from yamii.api import dependencies
from yamii.api.main import _check_ai_provider_cached, _reset_ai_health_cache


class CountingProvider:
    """health_check の呼び出し回数を数えるモック"""

    def __init__(self, ok: bool = True):
        self.ok = ok
        self.calls = 0

    async def health_check(self) -> bool:
        self.calls += 1
        return self.ok


@pytest.fixture(autouse=True)
def reset():
    _reset_ai_health_cache()
    dependencies.reset_dependencies()
    yield
    _reset_ai_health_cache()
    dependencies.reset_dependencies()


@pytest.mark.asyncio
async def test_repeated_checks_call_provider_once():
    """TTL 内の連続チェックでは AI プロバイダーを 1 回しか呼ばない"""
    provider = CountingProvider()
    dependencies.set_ai_provider(provider)  # type: ignore[arg-type]

    for _ in range(5):
        assert await _check_ai_provider_cached() is True

    assert provider.calls == 1


@pytest.mark.asyncio
async def test_failure_result_is_also_cached():
    """失敗結果もキャッシュされる（障害時の連打を防ぐ）"""
    provider = CountingProvider(ok=False)
    dependencies.set_ai_provider(provider)  # type: ignore[arg-type]

    assert await _check_ai_provider_cached() is False
    assert await _check_ai_provider_cached() is False
    assert provider.calls == 1
