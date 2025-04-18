export enum QUERY_KEYS {
    // AUTH KEYS
    CREATE_USER_ACCOUNT = "createUserAccount",
  
    // USER KEYS
    GET_CURRENT_USER = "getCurrentUser",
    GET_USERS = "getUsers",
    GET_USER_BY_ID = "getUserById",
    GET_SUGGESTED_TO_FOLLOW = "getSuggestedToFollow",
    GET_FOLLOWERS = "getFollowers",
    GET_FOLLOWEES = "getFollowees",
  
    // POST KEYS
    GET_POSTS = "getPosts",
    GET_INFINITE_POSTS = "getInfinitePosts",
    GET_RECENT_POSTS = "getRecentPosts",
    GET_POST_BY_ID = "getPostById",
    GET_POST_BY_USER = "getPostByUser",
    //GET_USER_POSTS = "getUserPosts",
    GET_FILE_PREVIEW = "getFilePreview",
    GET_FOLLOWEE_POSTS = "getFolloweePosts",
  
    //  SEARCH KEYS
    SEARCH_POSTS = "getSearchPosts",

    // LIKE KEYS
    LIKE_LIST = 'likeList',

    // SAVE KEYS
    SAVED_POSTS = 'savedPosts',

    // USER_KEYS
    GET_USER_INFO = 'getUserInfo',
  }