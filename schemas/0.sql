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
    foreign key (exception_id) references exception (id)
);

create table record (
    repository_id integer,
    machine_id integer,
    mode integer,
    elapsed_time real,
    unique (repository_id, machine_id, mode)
);