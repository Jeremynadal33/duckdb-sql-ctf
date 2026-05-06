from data_generator.generators.scenario5_graph import generate_graph
from data_generator.solutionators.scenario5_graph import solve


def test_solve_returns_canonical_flag(fake_config, tmp_path):
    generate_graph(fake_config, tmp_path, upload=False)
    flag = solve(fake_config, tmp_path, local=True)
    assert flag == fake_config.flag_scenario5
