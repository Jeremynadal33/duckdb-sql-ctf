from data_generator.generators.scenario1_logs import build_flag, generate_logs
from data_generator.solutionators.scenario1_logs import solve


def test_solve_returns_canonical_flag(fake_config, tmp_path):
    generate_logs(fake_config, tmp_path)
    flag = solve(fake_config, tmp_path, local=True)
    assert flag == build_flag(fake_config)
