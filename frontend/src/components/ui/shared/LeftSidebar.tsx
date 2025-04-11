import { useEffect } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { Button } from '../button'
import { useSignOutAccount } from '@/lib/react-query/queriesAndMutations'
import { useUserContext } from '@/context/AuthContext'
import { sidebarLinks } from '@/constants'
import { link } from 'fs'

const LeftSidebar = () => {
  const { pathname } = useLocation();
  const { mutate: signOut, isSuccess } = useSignOutAccount();
  const { user } = useUserContext();
  const navigate = useNavigate();
  useEffect(() => {
    if (isSuccess) {
      navigate(0);
    }
  }, [isSuccess])

  return (
    <nav className='leftsidebar'>
      <div className='flex flex-col gap-11'>
        <Link to="/" className="flex gap-3 items-center">
          <div className='flex items-center justify-start gap-3'>
            <img src='/assets/images/logo.svg' alt='logo' />
            <h2 className="h3-bold md:h2-bold text-primary-500">StudySphere</h2>
          </div>
        </Link>

        <Link to={`/profile/${user.user_id}`} className='flex gap-3 items-center'>

          <img src={user.avatarUrl || '/assets/icons/profile-placeholder.svg'}
            alt='profile'
            className='h-14 w-14 rounded-full' />

          <div className='flex flex-col'>

            <p className='body-bold text-light-1'>
              {user.name}
            </p>

          </div>
        </Link>

        <ul className='flex flex-col gap-6'>
          {sidebarLinks.map((link) => {
            const isActive = pathname === link.route;
            return (
              <li key={link.label} className={`leftsidebar-link group ${isActive && 'bg-primary-500'}`}>
                <NavLink to={link.route} className="flex gap-4 items-center p-4">
                  <img src={link.imgURL} alt={link.label} className={`group-hover:invert-white ${isActive && 'invert-white'}`} />
                  <p className={`group-hover:invert-white ${isActive && 'text-dark-1'} ${!isActive && 'text-primary-500'} `}>{link.label}</p>
                </NavLink>
              </li>
            )
          })}
        </ul>

      </div>
      <Button variant="ghost" className='shad-button_ghost'
        onClick={() => {
          //console.log('signout clicked');
          signOut();
          //console.log('signout success');
          }}>
        <img src='/assets/icons/logout.svg' alt='logout' />
        <p className='small-medium lg:base-medium text-primary-500'> Logout </p>
      </Button>

    </nav>
  )
}

export default LeftSidebar
