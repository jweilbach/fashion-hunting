/**
 * Tests for the Jobs API client
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { jobsApi } from '../jobs'
import apiClient from '../client'

// Mock the axios client
vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('jobsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getJobs', () => {
    it('should fetch all scheduled jobs', async () => {
      const mockResponse = {
        data: [
          {
            id: 'job-1',
            job_type: 'brand_monitoring',
            schedule_cron: '0 */6 * * *',
            enabled: true,
            config: { name: 'Morning Scan', brand_ids: ['b1', 'b2'] },
            run_count: 10,
          },
          {
            id: 'job-2',
            job_type: 'brand_monitoring',
            schedule_cron: '0 12 * * *',
            enabled: false,
            config: { name: 'Noon Scan', brand_ids: ['b3'] },
            run_count: 5,
          },
        ],
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await jobsApi.getJobs()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/jobs/')
      expect(result).toHaveLength(2)
      expect(result[0].schedule_cron).toBe('0 */6 * * *')
      expect(result[0].enabled).toBe(true)
    })

    it('should propagate API errors', async () => {
      const error = new Error('Unauthorized')
      vi.mocked(apiClient.get).mockRejectedValue(error)

      await expect(jobsApi.getJobs()).rejects.toThrow('Unauthorized')
    })
  })

  describe('getJob', () => {
    it('should fetch single job by ID', async () => {
      const mockResponse = {
        data: {
          id: 'job-123',
          job_type: 'brand_monitoring',
          schedule_cron: '0 8 * * *',
          enabled: true,
          config: {
            name: 'Daily Brand Check',
            brand_ids: ['brand-1', 'brand-2'],
            feed_ids: ['feed-1'],
          },
          run_count: 42,
          last_run: '2024-01-15T08:00:00Z',
          last_status: 'success',
          next_run: '2024-01-16T08:00:00Z',
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await jobsApi.getJob('job-123')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/jobs/job-123')
      expect(result.config.name).toBe('Daily Brand Check')
      expect(result.run_count).toBe(42)
      expect(result.last_status).toBe('success')
    })

    it('should propagate errors for non-existent jobs', async () => {
      const error = new Error('Job not found')
      vi.mocked(apiClient.get).mockRejectedValue(error)

      await expect(jobsApi.getJob('non-existent')).rejects.toThrow('Job not found')
    })
  })

  describe('createJob', () => {
    it('should create job with provided data', async () => {
      const newJob = {
        schedule_cron: '0 9 * * 1-5',
        enabled: true,
        config: {
          name: 'Weekday Morning Scan',
          brand_ids: ['brand-1'],
          feed_ids: ['feed-1', 'feed-2'],
        },
      }
      const mockResponse = {
        data: {
          id: 'new-job-id',
          job_type: 'brand_monitoring',
          run_count: 0,
          ...newJob,
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await jobsApi.createJob(newJob)

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/jobs/', newJob)
      expect(result.id).toBe('new-job-id')
      expect(result.config.name).toBe('Weekday Morning Scan')
      expect(result.run_count).toBe(0)
    })

    it('should propagate validation errors', async () => {
      const error = new Error('Invalid cron expression')
      vi.mocked(apiClient.post).mockRejectedValue(error)

      await expect(
        jobsApi.createJob({
          schedule_cron: 'invalid',
          config: { name: 'Bad Job', brand_ids: [], feed_ids: [] },
        })
      ).rejects.toThrow('Invalid cron expression')
    })
  })

  describe('updateJob', () => {
    it('should update job with provided data', async () => {
      const updateData = {
        enabled: false,
        schedule_cron: '0 10 * * *',
      }
      const mockResponse = {
        data: {
          id: 'job-123',
          job_type: 'brand_monitoring',
          schedule_cron: '0 10 * * *',
          enabled: false,
          config: { name: 'Updated Job', brand_ids: [], feed_ids: [] },
          run_count: 15,
        },
      }
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse)

      const result = await jobsApi.updateJob('job-123', updateData)

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/jobs/job-123', updateData)
      expect(result.enabled).toBe(false)
      expect(result.schedule_cron).toBe('0 10 * * *')
    })

    it('should update job config', async () => {
      const updateData = {
        config: {
          name: 'Renamed Job',
          brand_ids: ['brand-new'],
          feed_ids: [],
        },
      }
      const mockResponse = {
        data: {
          id: 'job-123',
          job_type: 'brand_monitoring',
          schedule_cron: '0 8 * * *',
          enabled: true,
          config: updateData.config,
          run_count: 20,
        },
      }
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse)

      const result = await jobsApi.updateJob('job-123', updateData)

      expect(result.config.name).toBe('Renamed Job')
      expect(result.config.brand_ids).toContain('brand-new')
    })
  })

  describe('deleteJob', () => {
    it('should delete job by ID', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({})

      await jobsApi.deleteJob('job-123')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/jobs/job-123')
    })

    it('should propagate deletion errors', async () => {
      const error = new Error('Cannot delete running job')
      vi.mocked(apiClient.delete).mockRejectedValue(error)

      await expect(jobsApi.deleteJob('job-123')).rejects.toThrow('Cannot delete running job')
    })
  })

  describe('runJobNow', () => {
    it('should trigger immediate job execution', async () => {
      const mockResponse = {
        data: {
          message: 'Job started successfully',
          job_id: 'job-123',
          status: 'running',
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await jobsApi.runJobNow('job-123')

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/jobs/job-123/run')
      expect(result.message).toBe('Job started successfully')
      expect(result.status).toBe('running')
    })

    it('should propagate errors when job cannot run', async () => {
      const error = new Error('Job already running')
      vi.mocked(apiClient.post).mockRejectedValue(error)

      await expect(jobsApi.runJobNow('job-123')).rejects.toThrow('Job already running')
    })
  })

  describe('getAllExecutions', () => {
    it('should fetch all job executions with default limit', async () => {
      const mockResponse = {
        data: [
          {
            id: 'exec-1',
            job_id: 'job-1',
            status: 'completed',
            items_processed: 50,
            items_failed: 2,
          },
          {
            id: 'exec-2',
            job_id: 'job-2',
            status: 'running',
            items_processed: 25,
            items_failed: 0,
          },
        ],
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await jobsApi.getAllExecutions()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/jobs/executions/?limit=100')
      expect(result).toHaveLength(2)
      expect(result[0].status).toBe('completed')
    })

    it('should support custom limit', async () => {
      const mockResponse = { data: [] }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await jobsApi.getAllExecutions(25)

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/jobs/executions/?limit=25')
    })
  })

  describe('getJobExecutions', () => {
    it('should fetch executions for specific job', async () => {
      const mockResponse = {
        data: [
          {
            id: 'exec-1',
            job_id: 'job-123',
            status: 'completed',
            started_at: '2024-01-15T08:00:00Z',
            completed_at: '2024-01-15T08:05:00Z',
            items_processed: 100,
            items_failed: 0,
          },
        ],
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await jobsApi.getJobExecutions('job-123')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/jobs/job-123/executions?limit=50')
      expect(result).toHaveLength(1)
      expect(result[0].job_id).toBe('job-123')
      expect(result[0].items_processed).toBe(100)
    })

    it('should support custom limit', async () => {
      const mockResponse = { data: [] }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await jobsApi.getJobExecutions('job-123', 10)

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/jobs/job-123/executions?limit=10')
    })
  })
})
