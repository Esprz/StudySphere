import { Models } from 'appwrite'
import React from 'react'
import { Button } from '../button'

type UserCardProps = {
    user: Models.Document
}

const UserCard = ({ user }: UserCardProps) => {
    return (
        <div className='user-card'>
            <img src={user.imageUrl || "/assets/icons/profile-placeholder.svg"}
                alt='user'
                className='rounded-full w-14 h-14' />
            <p className="base-medium text-light-1 text-center line-clamp-1">{user.name}</p>
            <p className="small-regular text-light-3 text-center line-clamp-1">@{user.username}</p>
            <Button type="button" size="sm" className="shad-button_primary px-5">
                Follow
            </Button>
        </div>
    )
}

export default UserCard
