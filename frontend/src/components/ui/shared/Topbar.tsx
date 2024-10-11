import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../button'
import { useSignOutAccount } from '@/lib/react-query/queriesAndMutations'
import { useUserContext } from '@/context/AuthContext'

const Topbar = () => {
  const { mutate: signOut, isSuccess } = useSignOutAccount();
  const { user } = useUserContext();
  const navigate = useNavigate();
  useEffect(() => {
    if (isSuccess) {
      navigate(0);
    }
  }, [isSuccess])

  return (
    <section className='topbar'>
      <div className='flex-between py-4 px-5'>
        <Link to="/" className="flex gap-3 items-center">
        <div className='flex items-center justify-start gap-3'>
            <img src='public/assets/images/logo.svg' alt='logo' width={45} />
            <h2 className="h3-bold md:h2-bold text-primary-500">StudySphere</h2>
          </div>
        </Link>

        <div className='flex gap-4'>
          <Button variant="ghost" className='shad-button_ghost'
            onClick={() => signOut}>
            <img src='public/assets/icons/logout.svg' alt='logout' />
          </Button>
          <Link to={`/profile/${user.id}`} className='flex-center gap-3'>
            <img src={user.imageUrl || 'public/assets/icons/profile-placeholder.svg'}
              alt='profile'
              className='h-8 w-8 rounded-full' />
          </Link>
        </div>

      </div>
    </section>
  )
}

export default Topbar
