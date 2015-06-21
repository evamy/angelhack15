drop table if exists entries;
drop table if exists votes;
create table entries (
    id INTEGER PRIMARY KEY autoincrement,
    mid text,
    title text not null,
    album text,
    artist text,
    filename text,
    length float,
    votes int default 0
);

create table votes (
    id INTEGER PRIMARY KEY autoincrement,
    sid INTEGER,
    ip text,
    FOREIGN KEY(sid) REFERENCES entries(id),
    UNIQUE (sid, ip)
);
