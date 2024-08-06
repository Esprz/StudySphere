import { bottombarLinks } from '@/constants';
import { Link, useLocation } from 'react-router-dom';

const Bottombar = () => {
  const { pathname } = useLocation();
  return (
    <section className='bottom-bar'>
      {bottombarLinks.map((link) => {
        const isActive = pathname === link.route;
        return (
          <Link to={link.route} key={link.label} className={`bottombar-link flex-col flex-center gap-1 group ${isActive && 'bg-primary-500 rounded-[10px]  p-2 transition'}`}>
            <img src={link.imgURL} alt={link.label} width={20} height={20} className={`${isActive && 'invert-white'}`} />
            <p className={`small-regular ${isActive && 'text-white'} ${!isActive && 'text-primary-500'}`}>{link.label}</p>
          </Link>

        )
      })}

    </section>
  )
}

export default Bottombar
