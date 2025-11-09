import { Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login';
import { EvaluationComponent } from './pages/evaluation/evaluation';
import { AuthGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'evaluation', component: EvaluationComponent, canActivate: [AuthGuard] },
  { path: '', redirectTo: '/evaluation', pathMatch: 'full' }
];