import { verifyAccessToken } from '../utils/jwt';

const auth = async (req: any, res: any, next: any) => {
    try {
        console.log('reach middleware auth', req.headers);
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({ message: 'Unauthorized' });
        }
        // Extract the token from the "Bearer <token>" format
        const token = authHeader.split(' ')[1];
        //console.log('auth header is valid => reach middleware 2');
        const decodedData = verifyAccessToken(token);
        //console.log('decodedData:', decodedData);
        req.userId = (decodedData as any)?.userId;
        //console.log('reach middleware next');
        next();
    } catch (error: any) {
        console.log('auth middleware error', error);
        res.status(401).json({ message: 'Invalid or expired token' });
    }
}

export default auth;