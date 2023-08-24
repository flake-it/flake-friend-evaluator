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
    foreign key (function_id) references function (id)
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
    foreign key (test_id) references test (id)
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
    foreign key (test_id) references test (id)
);

create table record (
    repository_id integer,
    machine_id integer,
    mode integer,
    elapsed_time real,
    unique (repository_id, machine_id, mode)
);