import { runService } from '@teamora/platform';
import { AppModule } from './app.module';
import { SERVICE } from './service';

void runService(SERVICE, (config) => AppModule.register(config));
