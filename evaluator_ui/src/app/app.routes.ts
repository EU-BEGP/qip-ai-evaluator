import { Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login';
import { EvaluationComponent } from './pages/evaluation/evaluation';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'evaluation', component: EvaluationComponent },
  { path: '', redirectTo: '/login', pathMatch: 'full' }
];
