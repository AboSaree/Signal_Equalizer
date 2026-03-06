import { Routes } from '@angular/router';
import { HomeComponent } from './pages/home/home.component';

export const routes: Routes = [
  {
    path: '',
    component: HomeComponent,
    title: 'Sofi — Feel Better'
  },
  // -------------------------------------------------------
  // ADD FUTURE ROUTES BELOW
  // Example:
  // {
  //   path: 'app',
  //   loadComponent: () => import('./pages/main-app/main-app.component')
  //                        .then(m => m.MainAppComponent),
  //   title: 'Sofi — Dashboard'
  // },
  // -------------------------------------------------------
  {
    path: '**',
    redirectTo: ''
  }
];
