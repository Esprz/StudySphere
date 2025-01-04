import { Models } from 'appwrite'
import React from 'react'
import Loader from './Loader'
import GridPostList from './GridPostList'
import { PPost } from '@/types/postgresTypes'
type SearchResultsProps = {
    isSearchFetching: boolean,
    searchedPosts: PPost[]
}

const SearchResults = ({ isSearchFetching, searchedPosts }: SearchResultsProps) => {
    if (isSearchFetching) return <Loader />
    if (searchedPosts && searchedPosts.length > 0)
        return (
            <GridPostList posts={searchedPosts} />
        )
    return (
        <p className='text-light-4 mt-10 text-center w-full'>No results found.</p>
    )
}

export default SearchResults
