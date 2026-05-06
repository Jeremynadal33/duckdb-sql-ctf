import os

import pytest

from data_generator.config import load_config
from data_generator.generators.scenario3_postgres import build_scenario3_flag
from data_generator.solutionators.scenario3_postgres import solve

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("CTF_INTEGRATION_TESTS") != "1",
    reason="Requires live PG + Nominatim (set CTF_INTEGRATION_TESTS=1)",
)
def test_solve_returns_canonical_flag(tmp_path):
    config = load_config()
    flag = solve(config, tmp_path)
    assert flag == build_scenario3_flag()
