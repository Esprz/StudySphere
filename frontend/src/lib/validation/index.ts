import { z } from "zod"

export const SignupValidation = z.object({
    name: z.string().min(2, { message: 'Too short' }),
    email: z.string().email(),
    password: z.string().min(8, { message: 'Password must be at least 8 characters' }),
})

export const SigninValidation = z.object({
    email: z.string().email(),
    password: z.string().min(8, { message: 'Password must be at least 8 characters' }),
})


export const PostValidation = z.object({
    title: z.string().min(3).max(1000),
    content: z.string().min(5).max(4200),
    images: z.custom<File[]>(),
    //location: z.string().min(2).max(100),
    //tags: z.string(),
})