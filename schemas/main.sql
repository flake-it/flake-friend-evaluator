create table repository (
    id integer primary key,
    name text,
    sha text,
    setup_commands text,
    run_commands text,
    environ text,
    unique (name, sha)
);

create table file (
    id integer primary key,
    file text,
    unique (file)
);

create table function (
    id integer primary key,
    file_id integer,
    line integer,
    name text,
    unique (file_id, line),
    foreign key (file_id) references file (id)
);

create table test (
    id integer primary key,
    repository_id integer,
    name text,
    function_id integer,
    unique (repository_id, name),
    foreign key (repository_id) references repository (id),
    foreign key (function_id) references function (id)
);

create table machine (
    id integer primary key,
    cpus real,
    read_kbps integer,
    write_kbps integer,
    unique (cpus, read_kbps, write_kbps)
);

create table exception (
    id integer primary key,
    exception text,
    unique (exception)
);

create table test_run (
    test_id integer,
    machine_id integer,
    exception_id integer,
    elapsed_time real,
    user_time real,
    system_time real,
    iowait_time real,
    read_count integer,
    write_count integer,
    context_switches integer,
    unique (test_id, machine_id),
    foreign key (test_id) references test (id),
    foreign key (machine_id) references machine (id),
    foreign key (exception_id) references exception (id)
);

create table function_call (
    id integer primary key,
    caller_id integer,
    callee_id integer,
    unique (caller_id, callee_id),
    foreign key (caller_id) references function (id),
    foreign key (callee_id) references function (id)
);

create table function_call_set (
    test_id integer,
    machine_id integer,
    mode integer,
    function_calls blob,
    unique (test_id, machine_id, mode),
    foreign key (test_id) references test (id),
    foreign key (machine_id) references machine (id)
);

create table line_arc (
    id integer primary key,
    file_id integer,
    line_from integer,
    line_to integer,
    unique (file_id, line_from, line_to),
    foreign key (file_id) references file (id)
);

create table line_arc_set (
    test_id integer,
    machine_id integer,
    mode integer,
    line_arcs blob,
    unique (test_id, machine_id, mode),
    foreign key (test_id) references test (id),
    foreign key (machine_id) references machine (id)
);

create table token (
    id integer primary key,
    token text,
    unique (token)
);

create table static_token_set (
    function_id integer,
    tokens blob,
    unique (function_id),
    foreign key (function_id) references function (id)
);

create table dynamic_token_set (
    test_id integer,
    machine_id integer,
    mode integer,
    tokens blob,
    unique (test_id, machine_id, mode),
    foreign key (test_id) references test (id),
    foreign key (machine_id) references machine (id)
);

create table static_metrics (
    function_id integer,
    ast_depth integer,
    external_modules integer,
    assertions integer,
    halstead_volume real,
    cyclomatic_complexity integer,
    test_lines_of_code integer,
    maintainability real,
    unique (function_id),
    foreign key (function_id) references function (id)
);

create table dynamic_metrics (
    test_id integer,
    machine_id integer,
    mode integer,
    elapsed_time real,
    user_time real,
    system_time real,
    iowait_time real,
    read_count integer,
    write_count integer,
    context_switches integer,
    covered_lines integer,
    max_threads integer,
    max_children integer,
    max_memory integer,
    unique (test_id, machine_id, mode),
    foreign key (test_id) references test (id),
    foreign key (machine_id) references machine (id)
);

create table record (
    repository_id integer,
    machine_id integer,
    mode integer,
    elapsed_time real,
    unique (repository_id, machine_id, mode),
    foreign key (repository_id) references repository (id),
    foreign key (machine_id) references machine (id)
);