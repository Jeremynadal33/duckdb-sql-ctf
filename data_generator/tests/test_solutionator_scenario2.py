from data_generator.generators.scenario1_logs import generate_logs
from data_generator.generators.scenario2_parquet import (
    build_employee_flag,
    generate_parquet,
)
from data_generator.solutionators.scenario2_parquet import solve


def test_solve_returns_canonical_flag(fake_config, tmp_path):
    generate_logs(fake_config, tmp_path)
    generate_parquet(fake_config, tmp_path)
    flag = solve(fake_config, tmp_path, local=True)
    assert flag == build_employee_flag(fake_config)
