import { INewPost, INewUser, IUpdatePost } from "@/types";
import { account, appwriteConfig, avatars, databases, storage } from "./config";
import { ID, ImageGravity, Query } from 'appwrite';

export async function createUserAccount(user: INewUser) {
    try {
        const newAccount = await account.create(
            ID.unique(),
            user.email,
            user.password,
            user.name
        );
        if (!newAccount) throw Error;

        const avatarUrl = avatars.getInitials(user.name);

        const newUser = await saveUserToDB({
            accountId: newAccount.$id,
            name: newAccount.name,
            email: newAccount.email,
            imageUrl: avatarUrl,
            username: user.username,
        });

        return newUser;

    } catch (error) {
        console.log(error);
        return error;
    }
}

export async function saveUserToDB(user: {
    accountId: string;
    email: string;
    name: string;
    imageUrl: URL;
    username?: string;
}) {
    try {
        const newUser = await databases.createDocument(
            appwriteConfig.databaseId,
            appwriteConfig.userCollectionId,
            ID.unique(),
            user,
        );
        return newUser;

    } catch (error) {
        console.log(error);
    }
}



export async function signInAccount(user: { email: string; password: string; }) {
    try {
        const sesstion = await account.createEmailPasswordSession(user.email, user.password);
        return sesstion;

    } catch (error) {
        console.log(error);
    }
}

export async function getCurrentUser() {
    try {
        const currentAccount = await account.get();
        if (!currentAccount) throw Error;

        const currentUser = await databases.listDocuments(
            appwriteConfig.databaseId,
            appwriteConfig.userCollectionId,
            [Query.equal('accountId', currentAccount.$id)]
        )
        if (!currentUser) throw Error;

        return currentUser.documents[0];

    } catch (error) {
        console.log(error);
        return null;

    }
}
    

export async function signOutAccount() {
    try {
        const sesstion = await account.deleteSession("current");
        return sesstion;

    } catch (error) {
        console.log(error);
    }
}

export async function createPost(post: INewPost) {
    try {
        // upload image
        const uploadedFile = await uploadFile(post.file[0]);
        if (!uploadedFile) throw Error;

        // image url
        const fileUrl = getFilePreview(uploadedFile.$id);
        if (!fileUrl) {
            deleteFile(uploadedFile.$id);
            throw Error;
        }

        // process tags
        const tags = post.tags?.replace(/ /g, '').split(',') || [];
        //console.log('fileUrl');
        //console.log(fileUrl);

        // create post
        const newPost = await databases.createDocument(
            appwriteConfig.databaseId,
            appwriteConfig.postCollectionId,
            ID.unique(),
            {
                creator: post.userId,
                caption: post.caption,
                imageUrl: fileUrl,
                imageId: uploadedFile.$id,
                location: post.location,
                tags: tags,
            }
        )
        if (!newPost) {
            await deleteFile(uploadedFile.$id);
            throw Error;
        }
        return newPost;

    } catch (error) {
        console.log(error);
    }
}

export async function uploadFile(file: File) {
    try {
        const uploadFile = await storage.createFile(
            appwriteConfig.storageId,
            ID.unique(),
            file
        );
        return uploadFile;

    } catch (error) {
        console.log(error);
    }
}

export function getFilePreview(fieldId: string) {
    try {
        const fileUrl = storage.getFileView(
            appwriteConfig.storageId,
            fieldId
        )
        if (!fileUrl) throw Error;
        return fileUrl;

    } catch (error) {
        console.log(error);
    }
}

export async function deleteFile(fieldId: string) {
    try {
        await storage.deleteFile(
            appwriteConfig.storageId,
            fieldId
        );
        return { status: 'ok' };

    } catch (error) {
        console.log(error);
    }
}

export async function getRecentPosts() {
    const posts = await databases.listDocuments(
        appwriteConfig.databaseId,
        appwriteConfig.postCollectionId,
        [Query.orderDesc(`$createdAt`), Query.limit(20)]
    )
    if (!posts) throw Error;
    return posts;
}

export async function likePost(postId: string, likesArray: string[]) {
    try {
        console.log('likePost')
        console.log(postId)
        const updatedPost = await databases.updateDocument(
            appwriteConfig.databaseId,
            appwriteConfig.postCollectionId,
            postId,
            {
                likes: likesArray
            }
        )
        if (!updatedPost) throw Error;
        return updatedPost;

    } catch (error) {
        console.log(error)
    }
}

export async function savePost(postId: string, userId: string) {
    try {
        const updatedPost = await databases.createDocument(
            appwriteConfig.databaseId,
            appwriteConfig.savesCollectionId,
            ID.unique(),
            {
                user: [userId],
                post: postId,
            }
        )
        if (!updatedPost) throw Error;
        return updatedPost;

    } catch (error) {
        console.log(error)
    }
}

export async function deleteSavePost(savedRecordId: string) {
    //console.log(savedRecordId)
    try {
        const statusCode = await databases.deleteDocument(
            appwriteConfig.databaseId,
            appwriteConfig.savesCollectionId,
            savedRecordId
        );
        if (!statusCode) throw Error;
        return { status: 'ok' };

    } catch (error) {
        console.log(error)
    }
}

export async function getPostById(postId: string) {
    try {
        const post = await databases.getDocument(
            appwriteConfig.databaseId,
            appwriteConfig.postCollectionId,
            postId
        )
        if (!post) throw Error;
        return post;
    } catch (error) {
        console.log(error);
    }
}

export async function updatePost(post: IUpdatePost) {
    console.log('api:updatePost')

    const hasFileToUpdate = post.file.length > 0;
    try {
        let image = {
            imageUrl: post.imageUrl,
            imageId: post.imageId
        }
        console.log('api:updatePost2')
        if (hasFileToUpdate) {
            console.log('api:updatePost3')
            // upload image
            const uploadedFile = await uploadFile(post.file[0]);
            if (!uploadedFile) throw Error;

            // image url
            const fileUrl = getFilePreview(uploadedFile.$id);
            if (!fileUrl) {
                deleteFile(uploadedFile.$id);
                throw Error;
            }
            image = { ...image, imageUrl: fileUrl, imageId: uploadedFile.$id };
        }


        // process tags
        const tags = post.tags?.replace(/ /g, '').split(',') || [];

        console.log('api:updatePost4')
        // update post
        const updatedPost = await databases.updateDocument(
            appwriteConfig.databaseId,
            appwriteConfig.postCollectionId,
            post.postId,
            {
                caption: post.caption,
                imageUrl: image.imageUrl,
                imageId: image.imageId,
                location: post.location,
                tags: tags,
            }
        );
        console.log('api:updatePost5')
        if (!updatedPost) {
            if (hasFileToUpdate) await deleteFile(post.imageId);
            throw Error;
        }
        if (hasFileToUpdate) await deleteFile(post.imageId);

        return updatedPost;

    } catch (error) {
        console.log(error);
    }
}

export async function deletePost(postId: string, imageId: string) {
    if (!postId || !imageId) throw Error;
    try {
        await databases.deleteDocument(
            appwriteConfig.databaseId,
            appwriteConfig.postCollectionId,
            postId
        );
        return { status: 'ok' };

    } catch (error) {
        console.log(error);
    }

}

export async function getInfinitePosts({ pageParam }: { pageParam: number }) {
    const queries = [] = [Query.orderDesc(`$updatedAt`), Query.limit(10)];
    if (pageParam){
        queries.push(Query.cursorAfter(pageParam.toString()));
    }
    try {
        const posts = await databases.listDocuments(
            appwriteConfig.databaseId,
            appwriteConfig.postCollectionId,
            queries
        )
        if (!posts) throw Error;
        return posts;

    } catch (error) {
        console.log(error);
    }
}

export async function searchPosts( searchTerm: string ) {    
    try {
        const posts = await databases.listDocuments(
            appwriteConfig.databaseId,
            appwriteConfig.postCollectionId,
            [Query.search('caption',searchTerm)]
        )
        if (!posts) throw Error;
        return posts;

    } catch (error) {
        console.log(error);
    }
}

export async function getUsers() {
    const users = await databases.listDocuments(
        appwriteConfig.databaseId,
        appwriteConfig.userCollectionId,
        [Query.orderDesc(`$createdAt`), Query.limit(20)]
    )
    if (!users) throw Error;
    return users;
}