module.exports = {
    clientId: 'studysphere',
    brokers: [
        process.env.KAFKA_BROKERS || 'localhost:9092'
    ],
    connectionTimeout: 3000,
    authenticationTimeout: 1000,
    reauthenticationThreshold: 10000,
    retry: {
        initialRetryTime: 100,
        retries: 8
    }
};