DROP DATABASE IF EXISTS photoshare;
CREATE DATABASE IF NOT EXISTS photoshare;
USE photoshare;
DROP TABLE IF EXISTS Pictures CASCADE;
DROP TABLE IF EXISTS Users CASCADE;

CREATE TABLE Users (
    user_id int4  AUTO_INCREMENT,
    email varchar(255) UNIQUE,
    password varchar(255),
    fname varchar(255),
    lname varchar(255),
    dob varchar(255),
    hometown varchar(510),
    gender varchar(255),
  CONSTRAINT users_pk PRIMARY KEY (user_id)
);

CREATE TABLE Albums (
    A_id int4 auto_increment,
    Name VARCHAR(255),
    Owner_id int4,
    CrDate TIMESTAMP,
    FOREIGN KEY (Owner_id) REFERENCES Users(user_id) ON DELETE CASCADE,
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

CREATE TABLE Comments (
	c_id int4 AUTO_INCREMENT,
    p_id int4,
    owner_id int4,
    text VARCHAR(1020),
    CrDate TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (p_id) REFERENCES Pictures(picture_id) ON DELETE CASCADE,
    PRIMARY KEY (c_id)    
);

CREATE TABLE Tags (
	Word VARCHAR(255),
    PRIMARY KEY (word)
);

CREATE TABLE Friends (
	user_id int4,
    frnd_id int4,
    PRIMARY KEY (user_id, frnd_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (frnd_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE AlbumPhotos (
	A_id int4,
    P_id int4,
    PRIMARY KEY (P_id, A_id),
    FOREIGN KEY (P_id) REFERENCES Pictures(picture_id) ON DELETE CASCADE,
    FOREIGN KEY (A_id) REFERENCES Albums(A_id) ON DELETE CASCADE
);

CREATE TABLE LikesPhoto (
	p_id int4,
    u_id int4,
    PRIMARY KEY (p_id, u_id),
    FOREIGN KEY (p_id) REFERENCES Pictures(picture_id) ON DELETE CASCADE,
    FOREIGN KEY (u_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE TaggedWith (
    tag VARCHAR(255),
    p_id int4,
    PRIMARY KEY (tag, p_id),
    FOREIGN KEY (tag) REFERENCES Tags(Word) ON DELETE CASCADE,
    FOREIGN KEY (p_id) REFERENCES Pictures(picture_id) ON DELETE CASCADE
);