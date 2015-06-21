drop table if exists entries;
create table entries (
    id int auto_increment,
    mid text primary key,
    title text not null,
    album text,
    artist text,
    filename text,
    length float
);
