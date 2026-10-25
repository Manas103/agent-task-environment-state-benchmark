from silicon.tasks import FAMILIES, N_PER_FAMILY, generate_all_tasks


def test_generates_300_tasks_in_5_families():
    tasks = generate_all_tasks()
    assert len(tasks) == 300
    for fam in FAMILIES:
        assert sum(1 for t in tasks if t.family == fam) == N_PER_FAMILY


def test_every_task_has_a_real_oracle_result():
    tasks = generate_all_tasks()
    for t in tasks:
        assert isinstance(t.oracle_result, bool)


def test_roughly_a_third_of_each_family_is_deliberately_wrong():
    tasks = generate_all_tasks()
    for fam in FAMILIES:
        fam_tasks = [t for t in tasks if t.family == fam]
        n_wrong = sum(1 for t in fam_tasks if t.is_wrong)
        assert n_wrong == 20
