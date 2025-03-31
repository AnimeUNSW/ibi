create domain zid as char(8)
	check (value ~ '^z[0-9]{7}');

create domain email as citext
	check (value ~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$');

create domain phone as varchar(15)
    check (value ~ '^(\+)[0-9]{6-14}+$');

create table users (
    id text primary key,
    first_name text not null,
    last_name text not null,
    zid zid unique,
    email email unique,
    phone_number phone unique,

    constraint validUser check (
        zid is not null and (email is null and phoneNumber is null) or
        zid is null and (email is not null and phoneNumber is not null) 
    )
);
