const path = require('path');
const fs = require('fs');

const rootKafkaConfig = path.join(__dirname, '../../kafka_config');
const backendKafkaConfig = path.join(__dirname, '../kafka_config');

if (!fs.existsSync(backendKafkaConfig)) {
    if (fs.existsSync(rootKafkaConfig)) {
        const linkType = process.platform === 'win32' ? 'junction' : 'dir';
        fs.symlinkSync(rootKafkaConfig, backendKafkaConfig, linkType);
        console.log('✅ Kafka config linked successfully');
    } else {
        console.warn('⚠️  Root kafka_config directory not found');
    }
} else {
    console.log('✅ Kafka config already exists');
}