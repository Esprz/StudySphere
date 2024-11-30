CREATE DATABASE Studysphere;
CREATE TABLE Users(
    user_id SERIAL PRIMARY KEY UNIQUE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    username VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    bio TEXT,
    avatar_url TEXT
);
CREATE TABLE Posts(
    post_id SERIAL PRIMARY KEY UNIQUE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    images TEXT[],
    author INTEGER NOT NULL,
    FOREIGN KEY (author) REFERENCES Users(user_id)
);
CREATE TABLE Likes(
    like_id SERIAL PRIMARY KEY UNIQUE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    creator INTEGER NOT NULL UNIQUE,
    post INTEGER NOT NULL UNIQUE,
    FOREIGN KEY (creator) REFERENCES Users(user_id),
    FOREIGN KEY (post) REFERENCES Posts(post_id)
);
CREATE TABLE Saves(
    save_id SERIAL PRIMARY KEY UNIQUE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    creator INTEGER NOT NULL UNIQUE,
    post INTEGER NOT NULL UNIQUE,
    FOREIGN KEY (creator) REFERENCES Users(user_id),
    FOREIGN KEY (post) REFERENCES Posts(post_id)
);
CREATE TABLE Comments(
    comment_id SERIAL PRIMARY KEY UNIQUE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    author INTEGER NOT NULL UNIQUE,
    post INTEGER NOT NULL UNIQUE,
    comment TEXT NOT NULL,
    FOREIGN KEY (author) REFERENCES Users(user_id),
    FOREIGN KEY (post) REFERENCES Posts(post_id)
);
CREATE TABLE Follows(
    follow_id SERIAL PRIMARY KEY UNIQUE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    follower INTEGER NOT NULL UNIQUE,
    followee INTEGER NOT NULL UNIQUE,
    FOREIGN KEY (follower) REFERENCES Users(user_id),
    FOREIGN KEY (followee) REFERENCES Posts(post_id)
);