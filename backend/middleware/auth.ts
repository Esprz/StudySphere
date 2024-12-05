import jwt from 'jsonwebtoken';

const auth = async (req: any, res: any, next: any) => {
    try {
        console.log('reach middleware auth', req.headers);
        const token = req.headers.authorization;
        //console.log('reach middleware 222222222222222');
        let decodedData: any;

        decodedData = jwt.verify(token, 'test');
        //console.log('decodedData:', decodedData);
        req.userId = decodedData?.user_id;
        //console.log('reach middleware 333333333333');
        next();
    } catch (error: any) {
        console.log('auth middleware error', error);
    }
}

export default auth;