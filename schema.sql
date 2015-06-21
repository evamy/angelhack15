drop table if exists entries;
create table entries (
    id text primary key,
    title text not null,
    album text,
    artist text,
    filename text,
    length float
);