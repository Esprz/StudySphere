import { Input } from "@/components/ui/input"
import GridPostList from "@/components/ui/shared/GridPostList";
import Loader from "@/components/ui/shared/Loader";
import SearchResults from "@/components/ui/shared/SearchResults";
import useDebounce from "@/hooks/useDebounce";
import { useGetPosts, useSearchPosts } from "@/lib/react-query/queriesAndMutations";
import { useEffect, useState } from 'react'
import { useInView } from "react-intersection-observer";


const Explore = () => {
  const { ref: inView } = useInView();
  const { data: posts, fetchNextPage, hasNextPage } = useGetPosts();
  const [searchValue, setSearchValue] = useState('');
  const debouncedValue = useDebounce(searchValue, 500);
  const { data: searchedPosts, isFetching: isSearchFetching } = useSearchPosts(debouncedValue);
  useEffect(() => {
    if (inView && !searchValue) fetchNextPage();
  }, [inView, searchValue])

  if (!posts) {
    return (
      <div className="flex-center w-full h-full">
        <Loader />
      </div>
    )
  }
  const shouldShowSearchResult = searchValue !== '';
  const shouldShowPosts = !shouldShowSearchResult && posts?.pages.every((item) => item.length === 0)

  return (
    <div className="explore-container">

      <div className="explore-inner_container">
        <h2 className="h3-bold md:h2-bold w-full">
          Search Posts
        </h2>
        <div className="flex gap-1 px-4 w-full rounded-lg bg-dark-2">
          <img src="/assets/icons/search.svg" width={24} height={24} alt="search" />
          <Input type="text"
            placeholder='Search'
            className="explore-search"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)} />
        </div>
      </div>

      <div className="w-full max-w-5xl mt-16 mb-7">
      {
      /*
      <div className="flex justify-end mb-4">
          <div className="flex gap-3 bg-dark-3 rounded-xl px-4 py-2 cusror-pointer">
            <p className="small-medium md:base-medium text-light-2">All</p>
            <img src="/assets/icons/filter.svg" alt="filter" width={20} />
          </div>
        </div>
      */}
        <div className="flex flex-wrap gap-9 w-full max-w-5xl">
          {shouldShowSearchResult
            ? (<SearchResults isSearchFetching={isSearchFetching} searchedPosts={searchedPosts} />)
            : shouldShowPosts
              ? (<p>posts</p>)
              : (posts.pages.map((item, index) => (
                <GridPostList key={`page-${index}`} posts={item} />
              )))}
        </div>
        {hasNextPage && !searchValue && (
          <div ref={inView} className="mt-10">
            <Loader />
          </div>
        )}
      </div>

    </div>
  )
}

export default Explore
