DROP DATABASE photoshare;
CREATE DATABASE IF NOT EXISTS photoshare;
USE photoshare;
DROP TABLE IF EXISTS Pictures CASCADE;
DROP TABLE IF EXISTS Users CASCADE;

CREATE TABLE Users (
    user_id int4  AUTO_INCREMENT,
    email varchar(255) UNIQUE,
    password varchar(255),
  CONSTRAINT users_pk PRIMARY KEY (user_id)
);

CREATE TABLE Albums (
    A_id int4 auto_increment,
    Name VARCHAR(255),
    Owner_id int4,
    CrDate TIMESTAMP,
    FOREIGN KEY (Owner_id) REFERENCES Users(user_id),
    PRIMARY KEY (A_id)
);

CREATE TABLE Pictures
(
  picture_id int4  AUTO_INCREMENT,
  user_id int4,
  imgdata longblob ,
  caption VARCHAR(255),
  INDEX upid_idx (user_id),
  CONSTRAINT pictures_pk PRIMARY KEY (picture_id)
);

CREATE TABLE Friends (
	user_id int4,
    frnd_id int4,
    PRIMARY KEY (user_id, frnd_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (frnd_id) REFERENCES Users(user_id)
);

CREATE TABLE Tags (
	Word VARCHAR(255),
    PRIMARY KEY (word)
);

INSERT INTO Users (email, password) VALUES ('test@bu.edu', 'test');
INSERT INTO Users (email, password) VALUES ('test1@bu.edu', 'test');
INSERT INTO Tags (Word) VALUES ('nature');