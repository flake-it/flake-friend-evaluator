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

create table record (
    repository_id integer,
    machine_id integer,
    mode integer,
    elapsed_time real,
    unique (repository_id, machine_id, mode)
);