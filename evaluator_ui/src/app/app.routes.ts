import { Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login';
import { EvaluationComponent } from './pages/evaluation/evaluation';
import { AuthGuard } from './guards/auth.guard';
import { Modules } from './pages/modules/modules';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'evaluation/:id', component: EvaluationComponent, canActivate: [AuthGuard] },
  { path: 'modules', component: Modules, canActivate: [AuthGuard] },
  { path: '', redirectTo: '/modules', pathMatch: 'full' }
];