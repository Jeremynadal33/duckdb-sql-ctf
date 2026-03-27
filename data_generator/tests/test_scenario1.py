import json
import zipfile

import pytest

from data_generator.constants import FIGURANT_NAMES, QUACKIE_VARIATIONS
from data_generator.generators.scenario1_logs import (
    NUM_FILES,
    NUM_NOISE_UNRETURNED,
    NUM_SUSPECT_LOGS,
    RECORDS_PER_FILE,
    TOTAL_RECORDS,
    build_flag,
    generate_logs,
    split_flag,
)


class TestBuildFlag:
    def test_flag_format(self, fake_config):
        flag = build_flag(fake_config)
        assert flag.startswith("FLAG{")
        assert flag.endswith("}")
        assert f"aws_access_key_id={fake_config.iam_access_key_id}" in flag
        assert f"aws_secret_access_key={fake_config.iam_secret_access_key}" in flag
        assert f"bucket={fake_config.s3_bucket_name}" in flag


class TestSplitFlag:
    def test_concatenation_equals_original(self, fake_config):
        flag = build_flag(fake_config)
        fragments = split_flag(flag)
        assert len(fragments) == 12
        assert "".join(fragments) == flag

    def test_fragments_roughly_equal(self, fake_config):
        flag = build_flag(fake_config)
        fragments = split_flag(flag)
        lengths = [len(f) for f in fragments]
        assert max(lengths) - min(lengths) <= 1

    def test_no_empty_fragments(self, fake_config):
        flag = build_flag(fake_config)
        fragments = split_flag(flag)
        assert all(len(f) > 0 for f in fragments)


class TestGenerateLogs:
    @pytest.fixture
    def zip_path(self, fake_config, tmp_path):
        return generate_logs(fake_config, tmp_path)

    def test_zip_has_500_files(self, zip_path):
        with zipfile.ZipFile(zip_path) as zf:
            assert len(zf.namelist()) == NUM_FILES

    def test_each_file_has_100_records(self, zip_path):
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                records = json.loads(zf.read(name))
                assert len(records) == RECORDS_PER_FILE

    def test_total_record_count(self, zip_path):
        total = 0
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                records = json.loads(zf.read(name))
                total += len(records)
        assert total == TOTAL_RECORDS

    def test_unreturned_count(self, zip_path):
        unreturned = 0
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                records = json.loads(zf.read(name))
                unreturned += sum(1 for r in records if r["timestamp_return"] is None)
        assert unreturned == NUM_SUSPECT_LOGS + NUM_NOISE_UNRETURNED

    def test_suspect_birth_certificates_count(self, zip_path):
        suspects = []
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                records = json.loads(zf.read(name))
                for r in records:
                    if (
                        r["timestamp_return"] is None
                        and r["document_type"] == "acte_de_naissance"
                    ):
                        suspects.append(r)
        assert len(suspects) == NUM_SUSPECT_LOGS

    def test_suspects_in_different_files(self, zip_path):
        files_with_suspects = set()
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                records = json.loads(zf.read(name))
                for r in records:
                    if (
                        r["timestamp_return"] is None
                        and r["document_type"] == "acte_de_naissance"
                    ):
                        files_with_suspects.add(name)
        assert len(files_with_suspects) == NUM_SUSPECT_LOGS

    def test_flag_reconstruction_from_chronological_order(self, fake_config, zip_path):
        """Sort suspects by timestamp_checkout, concatenate notes → flag."""
        suspects = []
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                records = json.loads(zf.read(name))
                for r in records:
                    if (
                        r["timestamp_return"] is None
                        and r["document_type"] == "acte_de_naissance"
                    ):
                        suspects.append(r)

        suspects.sort(key=lambda r: r["timestamp_checkout"])
        reconstructed = "".join(r["metadata"]["notes"] for r in suspects)
        expected = build_flag(fake_config)
        assert reconstructed == expected

    def test_suspect_borrower_names_are_variations(self, zip_path):
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                records = json.loads(zf.read(name))
                for r in records:
                    if (
                        r["timestamp_return"] is None
                        and r["document_type"] == "acte_de_naissance"
                    ):
                        assert r["borrower_name"] in QUACKIE_VARIATIONS

    def test_normal_logs_use_figurant_names(self, zip_path):
        with zipfile.ZipFile(zip_path) as zf:
            # Check a sample of files
            for name in list(zf.namelist())[:5]:
                records = json.loads(zf.read(name))
                for r in records:
                    if r["timestamp_return"] is not None:
                        assert r["borrower_name"] in FIGURANT_NAMES
