locals {
  my_ip_cidr = "${chomp(data.http.my_ip.response_body)}/32"

  dbname = "ctfdb"

  # ── CTF flags (must mirror the Python logic in data_generator/src/data_generator/generators/) ──
  db_host = split(":", aws_db_instance.ctf.endpoint)[0]
  db_port = "5432"

  flag_scenario1 = "FLAG{aws_access_key_id=${aws_iam_access_key.ctf.id},aws_secret_access_key=${aws_iam_access_key.ctf.secret},bucket=${aws_s3_bucket.ctf.bucket}}"
  flag_scenario2 = "FLAG{pg_host=${local.db_host},pg_port=${local.db_port},pg_user=${postgresql_role.readonly.name},pg_password=${postgresql_role.readonly.password},pg_dbname=${local.dbname}}"
  # flag_scenario3 is owned by the Python data generator (computed from GH_PAGES_BASE_URL + QUACKIE_DEATH_DATE)
  flag_scenario4 = "FLAG{graph_source=tbd,graph_access=tbd}"
  flag_scenario5 = "FLAG{canards_anti_criminels_mission_accomplie}"

  # The hash of the answer checker image, used to trigger rebuilds when source files change
  answer_checker_src = fileset("${path.module}/../answer_checker", "src/**/*.py")
  answer_checker_hash = sha1(join("", [
    for f in local.answer_checker_src : filesha1("${path.module}/../answer_checker/${f}")
  ]))
}
