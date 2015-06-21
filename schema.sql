drop table if exists entries;
create table entries (
    id INTEGER PRIMARY KEY autoincrement,
    mid text,
    title text not null,
    album text,
    artist text,
    filename text,
    length float
);
