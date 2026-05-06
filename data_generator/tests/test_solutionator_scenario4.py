from data_generator.generators.scenario4_iceberg import generate_iceberg
from data_generator.solutionators.scenario4_iceberg import solve


def test_solve_returns_canonical_flag(fake_config, tmp_path):
    generate_iceberg(fake_config, tmp_path, upload=False)
    flag = solve(fake_config, tmp_path, local=True)
    assert flag == fake_config.flag_scenario4
