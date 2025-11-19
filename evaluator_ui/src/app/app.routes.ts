import { Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login';
import { EvaluationComponent } from './pages/evaluation/evaluation';
import { AuthGuard } from './guards/auth.guard';
import { Modules } from './pages/modules/modules';
import { Notifications } from './pages/notifications/notifications';
import { MainLayout } from './pages/main-layout/main-layout';

export const routes: Routes = [
  {
    path: '',
    component: MainLayout,
    children: [
      { 
        path: '', 
        redirectTo: '/modules', 
        pathMatch: 'full' 
      },
      { 
        path: 'modules', 
        component: Modules, 
        canActivate: [AuthGuard] 
      },
      { 
        path: 'notifications', 
        component: Notifications, 
        canActivate: [AuthGuard] 
      }, 
      { 
        path: 'evaluation/:id', 
        component: EvaluationComponent, 
        canActivate: [AuthGuard] 
      }
    ]
  },
  { 
    path: 'login', 
    component: LoginComponent 
  }
];