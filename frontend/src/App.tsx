import AuthLayout from './_auth/AuthLayout';
import SigninForm from './_auth/forms/SigninForm';
import SignupForm from './_auth/forms/SignupForm';
import { CreatePost, EditPost, Explore, Home, PostDetails, Profile, Saved, MyFocus, Friends } from './_root/pages';
import RootLayout from './_root/RootLayout';
import { Toaster } from './components/ui/toaster';
import './globals.css';
import { Routes, Route } from 'react-router-dom';
const App = () => {
  return (
    <main className='flex xl:h-screen min-h-screen'>
      <Routes>

        {/* public routes (every one can see)*/}
        <Route element={<AuthLayout />}>
          <Route path='/sign-in' element={<SigninForm />} />
          <Route path='/sign-up' element={<SignupForm />} />
        </Route>


        {/* private routes (after sign in)*/}
        <Route element={<RootLayout />}>
          <Route index element={<Home />} />
          <Route path="/explore" element={<Explore />} />          
          <Route path="/my-focus" element={<MyFocus />} />          
          <Route path="/friends" element={<Friends />} /> 
          <Route path="/saved" element={<Saved />} />         
          <Route path="/create-post" element={<CreatePost />} />

          <Route path="/update-post/:id" element={<EditPost />} />
          <Route path="/post/:id" element={<PostDetails />} />
          <Route path="/profile/:username" element={<Profile />} />
        </Route>

      </Routes>
      <Toaster />
    </main>
  )
}

export default App
