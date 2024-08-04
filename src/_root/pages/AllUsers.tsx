import Loader from '@/components/ui/shared/Loader';
import UserCard from '@/components/ui/shared/UserCard';
import { useGetUsers } from '@/lib/react-query/queriesAndMutations'
import { Models } from 'appwrite';


const AllUsers = () => {
  const { data: users, isLoading: isLoadingAllUsers } = useGetUsers();

  if (isLoadingAllUsers) {
    return <Loader />
  }

  console.log(users);

  return (
    <div className='common-container'>
      <div className='user-container'>
        <ul className="user-grid">
          {!users?.documents || users?.documents.length === 0
            ? (<p>No Users</p>)
            : (users?.documents.map((user: Models.Document) => (
              <UserCard key={user.$id} user={user} />
            )))
          }
        </ul>
      </div>
    </div>
  )
}

export default AllUsers
